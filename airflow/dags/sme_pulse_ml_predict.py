"""
SME Pulse ML Prediction Pipeline
DAG chạy inference cho các ML models sau khi ETL hoàn tất

Schedule: None (Triggered by sme_pulse_daily_etl)
Tasks:
  - UC09: Prophet cashflow forecasting (30 days ahead)
  - UC10: Isolation Forest anomaly detection (last 7 days)
  - Refresh serving layer (Metabase + Redis cache)
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
import logging
import os
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///opt/airflow/mlflow")

CONFIG_PATH = Path(__file__).parent / "config" / "pipeline_config.yml"
with open(CONFIG_PATH, 'r') as f:
    PIPELINE_CONFIG = yaml.safe_load(f)

# Default DAG arguments
default_args = {
    'owner': 'ml-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
    'execution_timeout': timedelta(minutes=30)
}


# ============================================================================
# TASK FUNCTIONS
# ============================================================================

def refresh_metabase_cache(**context):
    """
    Refresh Metabase cache after ML predictions
    """
    logger.info("Refreshing Metabase cache...")

    try:
        metabase_config = PIPELINE_CONFIG.get('metabase', {})
        if not metabase_config.get('enabled', True):
            logger.info("Metabase integration disabled, skipping...")
            return

        try:
            import requests
        except ImportError:
            logger.warning("requests library not available, skipping Metabase refresh")
            return

        session_token = os.getenv('METABASE_API_KEY') or metabase_config.get('api_key')
        if not session_token:
            logger.warning("METABASE_API_KEY not configured, skipping Metabase refresh")
            return

        database_id = metabase_config.get('ml_database_id', metabase_config.get('database_id', 1))
        url = f"{metabase_config.get('url', 'http://metabase:3000')}/api/database/{database_id}/sync_schema"
        response = requests.post(
            url,
            headers={'X-Metabase-Session': session_token},
            timeout=30
        )

        if response.status_code == 200:
            logger.info("✅ Metabase cache refreshed successfully after ML predictions")
            context['ti'].xcom_push(key='metabase_cache_status', value='success')
        else:
            logger.warning(f"Metabase refresh returned status {response.status_code}")
            context['ti'].xcom_push(key='metabase_cache_status', value='warning')
    except Exception as e:
        logger.warning(f"⚠️ Metabase cache refresh failed: {e}")
        context['ti'].xcom_push(key='metabase_cache_status', value='failed')


def invalidate_redis_cache(**context):
    """
    Invalidate Redis cache after ML predictions
    """
    logger.info("Invalidating Redis cache...")

    try:
        redis_config = PIPELINE_CONFIG.get('redis', {})
        if not redis_config.get('enabled', True):
            logger.info("Redis integration disabled, skipping...")
            return

        try:
            import redis
        except ImportError:
            logger.warning("redis library not available, skipping cache invalidation")
            return

        client = redis.Redis(
            host=redis_config.get('host', 'redis'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0),
            password=redis_config.get('password'),
            socket_connect_timeout=5,
        )
        client.ping()

        patterns = redis_config.get('ml_cache_patterns') or redis_config.get('cache_patterns', ['sme:gold:*'])
        total_deleted = 0

        for pattern in patterns:
            keys = client.keys(pattern)
            if keys:
                deleted = client.delete(*keys)
                total_deleted += deleted
                logger.info(f"Deleted {deleted} Redis keys matching '{pattern}'")

        logger.info(f"✅ Redis cache invalidation completed, deleted={total_deleted}")
        context['ti'].xcom_push(key='redis_cache_deleted', value=total_deleted)
    except Exception as e:
        logger.warning(f"⚠️ Redis cache invalidation failed: {e}")
        context['ti'].xcom_push(key='redis_cache_deleted', value=-1)


def predict_cashflow_uc09(**context):
    """
    UC09: Prophet Cashflow Forecasting
    Load model -> Predict 30 days -> Save to Gold layer
    """
    logger.info("Starting UC09 Cashflow Forecasting...")
    
    import subprocess
    import os
    
    # Set MLflow tracking URI
    env = os.environ.copy()
    env['MLFLOW_TRACKING_URI'] = MLFLOW_TRACKING_URI
    
    result = subprocess.run(
        ['python', '/opt/ops/ml/UC09-forecasting/predict_cashflow.py'],
        capture_output=True,
        text=True,
        timeout=600,  # 10 min timeout
        env=env
    )
    
    if result.returncode != 0:
        logger.error(f"UC09 failed: {result.stderr}")
        raise Exception(f"Cashflow prediction failed: {result.stderr}")
    
    logger.info(f"UC09 output: {result.stdout}")
    logger.info("✅ UC09 Cashflow forecasting completed")
    
    # Push metrics to XCom
    context['ti'].xcom_push(key='uc09_status', value='success')


def detect_anomalies_uc10(**context):
    """
    UC10: Isolation Forest Anomaly Detection
    Load model -> Detect anomalies -> Save alerts to Gold layer
    """
    logger.info("Starting UC10 Anomaly Detection...")
    
    import subprocess
    import os
    
    # Set MLflow tracking URI
    env = os.environ.copy()
    env['MLFLOW_TRACKING_URI'] = MLFLOW_TRACKING_URI
    
    result = subprocess.run(
        ['python', '/opt/ops/ml/UC10-anomoly_detection/ops-ML-anomaly_detection/detect_anomalies.py'],
        capture_output=True,
        text=True,
        timeout=600,  # 10 min timeout
        env=env
    )
    
    if result.returncode != 0:
        logger.error(f"UC10 failed: {result.stderr}")
        raise Exception(f"Anomaly detection failed: {result.stderr}")
    
    logger.info(f"UC10 output: {result.stdout}")
    logger.info("✅ UC10 Anomaly detection completed")
    
    # Push metrics to XCom
    context['ti'].xcom_push(key='uc10_status', value='success')


# ============================================================================
# DAG DEFINITION
# ============================================================================

with DAG(
    dag_id='sme_pulse_ml_predict',
    default_args=default_args,
    description='ML Inference Pipeline (UC09 + UC10)',
    schedule_interval=None,  # Triggered by sme_pulse_daily_etl
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['ml', 'prediction', 'serving']
) as dag:
    
    # Task 1: UC09 Cashflow Forecasting
    predict_cashflow_task = PythonOperator(
        task_id='predict_cashflow_uc09',
        python_callable=predict_cashflow_uc09,
        execution_timeout=timedelta(minutes=10)
    )
    
    # Task 2: UC10 Anomaly Detection
    detect_anomalies_task = PythonOperator(
        task_id='detect_anomalies_uc10',
        python_callable=detect_anomalies_uc10,
        execution_timeout=timedelta(minutes=10)
    )
    
    # Task 3-4: Serve Layer (Refresh caches after predictions)
    with TaskGroup('serve_layer', tooltip='Update serving layer with ML predictions') as serve_group:
        refresh_metabase_task = PythonOperator(
            task_id='refresh_metabase',
            python_callable=refresh_metabase_cache,
            execution_timeout=timedelta(minutes=5)
        )
        
        invalidate_redis_task = PythonOperator(
            task_id='invalidate_redis',
            python_callable=invalidate_redis_cache,
            execution_timeout=timedelta(minutes=5)
        )
        
        # Parallel execution
        [refresh_metabase_task, invalidate_redis_task]
    
    # ============================================================================
    # TASK DEPENDENCIES
    # ============================================================================
    
    # Run predictions in parallel, then refresh serving layer
    [predict_cashflow_task, detect_anomalies_task] >> serve_group
