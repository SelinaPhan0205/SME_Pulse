"""
DAG for ML Cashflow Forecasting (UC09)
- Train Prophet model weekly
- Run predictions daily
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import sys
import os

# Thêm ops vào Python path
sys.path.insert(0, '/opt/ops')

default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG 1: Train model weekly (chạy mỗi Chủ nhật)
dag_train = DAG(
    'sme_pulse_ml_train_cashflow',
    default_args=default_args,
    description='Train Prophet model for cashflow forecasting',
    schedule_interval='0 2 * * 0',  # 2 AM every Sunday
    catchup=False,
    tags=['ml', 'prophet', 'cashflow', 'training'],
)

train_model = BashOperator(
    task_id='train_prophet_model',
    bash_command='cd /opt && python -m ops.ml.train_cashflow_model',
    dag=dag_train,
)

# DAG 2: Predict daily (chạy hàng ngày sau khi có data mới)
dag_predict = DAG(
    'sme_pulse_ml_predict_cashflow',
    default_args=default_args,
    description='Daily cashflow prediction using Prophet',
    schedule_interval='0 6 * * *',  # 6 AM every day
    catchup=False,
    tags=['ml', 'prophet', 'cashflow', 'prediction'],
)

run_prediction = BashOperator(
    task_id='predict_cashflow',
    bash_command='cd /opt && python -m ops.ml.predict_cashflow',
    dag=dag_predict,
)

# Validation task: Check if predictions are saved
validate_prediction = BashOperator(
    task_id='validate_prediction',
    bash_command="""
    docker compose exec trino trino --catalog sme_lake --schema gold --execute \
    "SELECT COUNT(*) as prediction_count FROM ml_cashflow_forecast WHERE prediction_timestamp >= current_date"
    """,
    dag=dag_predict,
)

run_prediction >> validate_prediction
