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
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup
import logging

logger = logging.getLogger(__name__)

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
        import requests
        # Placeholder - implement actual Metabase API call
        logger.info("✅ Metabase cache refresh skipped (not configured)")
    except Exception as e:
        logger.warning(f"⚠️ Metabase cache refresh failed: {e}")


def invalidate_redis_cache(**context):
    """
    Invalidate Redis cache after ML predictions
    """
    logger.info("Invalidating Redis cache...")
    try:
        import redis
        # Placeholder - implement actual Redis invalidation
        logger.info("✅ Redis cache invalidation skipped (not configured)")
    except Exception as e:
        logger.warning(f"⚠️ Redis cache invalidation failed: {e}")


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
    env['MLFLOW_TRACKING_URI'] = 'file:///tmp/mlflow'
    
    result = subprocess.run(
        ['python', '/opt/ops/ML-prophet_forcasting/predict_cashflow.py'],
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
    env['MLFLOW_TRACKING_URI'] = 'file:///tmp/airflow_mlflow'
    
    result = subprocess.run(
        ['python', '/opt/ops/ML-anomaly_detection/detect_anomalies.py'],
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
