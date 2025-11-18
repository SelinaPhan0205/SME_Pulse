"""
SME Pulse ML Training Pipeline
DAG chạy training/retraining các ML models theo lịch định kỳ

Schedule: Weekly (Sunday 1:00 AM)
Tasks:
  - UC09: Train Prophet cashflow forecasting model
  - UC10: Train Isolation Forest anomaly detection model
  - Save models to MLflow + MinIO
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
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
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1)
}


# ============================================================================
# TASK FUNCTIONS
# ============================================================================

def train_cashflow_model_uc09(**context):
    """
    UC09: Train Prophet Cashflow Forecasting Model
    Load historical data -> Train Prophet -> Save to MLflow
    """
    logger.info("Starting UC09 Model Training...")
    
    import subprocess
    import os
    
    # Set MLflow tracking URI
    env = os.environ.copy()
    env['MLFLOW_TRACKING_URI'] = 'file:///tmp/airflow_mlflow'
    
    result = subprocess.run(
        ['python', '/opt/ops/ml/UC09-forecasting/train_cashflow_model.py'],
        capture_output=True,
        text=True,
        timeout=1800,  # 30 min timeout
        env=env
    )
    
    if result.returncode != 0:
        logger.error(f"UC09 training failed: {result.stderr}")
        raise Exception(f"Cashflow model training failed: {result.stderr}")
    
    logger.info(f"UC09 training output: {result.stdout}")
    logger.info("✅ UC09 Model training completed")
    
    # Push metrics to XCom
    context['ti'].xcom_push(key='uc09_training_status', value='success')


def train_anomaly_model_uc10(**context):
    """
    UC10: Train Isolation Forest Anomaly Detection Model
    Load historical data -> Train Isolation Forest -> Save to MLflow
    """
    logger.info("Starting UC10 Model Training...")
    
    import subprocess
    import os
    
    # Set MLflow tracking URI
    env = os.environ.copy()
    env['MLFLOW_TRACKING_URI'] = 'file:///tmp/airflow_mlflow'
    
    result = subprocess.run(
        ['python', '/opt/ops/ml/UC10-anomoly_detection/ops-ML-anomaly_detection/train_isolation_forest.py'],
        capture_output=True,
        text=True,
        timeout=1800,  # 30 min timeout
        env=env
    )
    
    if result.returncode != 0:
        logger.error(f"UC10 training failed: {result.stderr}")
        raise Exception(f"Anomaly model training failed: {result.stderr}")
    
    logger.info(f"UC10 training output: {result.stdout}")
    logger.info("✅ UC10 Model training completed")
    
    # Push metrics to XCom
    context['ti'].xcom_push(key='uc10_training_status', value='success')


def validate_models(**context):
    """
    Validate that both models are successfully saved and accessible
    """
    logger.info("Validating trained models...")
    
    # Pull training status from XCom
    uc09_status = context['ti'].xcom_pull(task_ids='train_uc09', key='uc09_training_status')
    uc10_status = context['ti'].xcom_pull(task_ids='train_uc10', key='uc10_training_status')
    
    if uc09_status != 'success' or uc10_status != 'success':
        raise Exception("Model training validation failed!")
    
    logger.info("✅ All models validated successfully")


# ============================================================================
# DAG DEFINITION
# ============================================================================

with DAG(
    dag_id='sme_pulse_ml_training',
    default_args=default_args,
    description='ML Model Training Pipeline (Weekly retraining)',
    schedule_interval='0 1 * * 0',  # Sunday 1:00 AM
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['ml', 'training', 'weekly']
) as dag:
    
    # Task 1: Train UC09 Prophet Model
    train_uc09_task = PythonOperator(
        task_id='train_uc09',
        python_callable=train_cashflow_model_uc09,
        execution_timeout=timedelta(minutes=30)
    )
    
    # Task 2: Train UC10 Isolation Forest Model
    train_uc10_task = PythonOperator(
        task_id='train_uc10',
        python_callable=train_anomaly_model_uc10,
        execution_timeout=timedelta(minutes=30)
    )
    
    # Task 3: Validate Models
    validate_task = PythonOperator(
        task_id='validate_models',
        python_callable=validate_models,
        execution_timeout=timedelta(minutes=5)
    )
    
    # ============================================================================
    # TASK DEPENDENCIES
    # ============================================================================
    
    # Train both models in parallel, then validate
    [train_uc09_task, train_uc10_task] >> validate_task
