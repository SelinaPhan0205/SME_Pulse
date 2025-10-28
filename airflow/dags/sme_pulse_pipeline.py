"""
SME Pulse Data Pipeline - Airflow DAG
======================================
Pipeline: Bronze (ingest) → Silver (staging) → Gold (facts) → Metabase
Schedule: Daily at 00:00 (midnight)
Owner: Data Team
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable

# =====================================================
# DAG Configuration
# =====================================================
default_args = {
    'owner': 'data-team',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
}

dag = DAG(
    dag_id='sme_pulse_pipeline',
    default_args=default_args,
    description='SME Pulse: Bronze → Silver → Gold data pipeline',
    schedule_interval='0 0 * * *',  # Daily at midnight
    catchup=False,
    tags=['sme_pulse', 'data_pipeline', 'production'],
)

# =====================================================
# Python Functions for Tasks
# =====================================================

def success_notification(**context):
    """Print success message"""
    execution_date = context['execution_date']
    print(f"✅ Pipeline completed successfully at {execution_date}")
    print("📊 Data available in Metabase: gold.mart.fact_sales")

def failure_notification(**context):
    """Print failure message"""
    task_instance = context['task_instance']
    print(f"❌ Pipeline failed at task: {task_instance.task_id}")
    print(f"Error: {task_instance.xcom_pull(task_ids=task_instance.task_id)}")

# =====================================================
# Task 1: Ingest Bronze Data
# =====================================================
task_ingest_bronze = BashOperator(
    task_id='ingest_bronze',
    bash_command='''
    python /opt/ops/ingest_bronze_raw.py
    ''',
    dag=dag,
    doc='''
    **Task**: Ingest raw data into Bronze layer
    - Source: CSV files from data/ folder
    - Destination: MinIO s3://bronze/raw/
    - Format: Parquet
    - Expected rows: ~831,966
    '''
)

# =====================================================
# Task 2: dbt deps skipped (packages already installed)
# =====================================================
# NOTE: dbt_utils already exists in /opt/dbt/dbt_packages/
# No need to re-download, avoid permission issues

# =====================================================
# Task 3: Run dbt Staging (Silver layer)
# =====================================================
task_dbt_staging = BashOperator(
    task_id='dbt_staging',
    bash_command='''
    export DBT_LOG_PATH=/tmp && cd /opt/dbt && dbt run --select staging --profiles-dir . --target dev --no-version-check --target-path /tmp/dbt_target 2>&1
    ''',
    dag=dag,
    doc='''
    **Task**: Transform Bronze → Silver (Staging)
    - Model: stg_transactions
    - Schema: silver.core
    - Location: s3a://silver/warehouse/core/
    - Data quality: Convert negative values to 0
    - Expected rows: 831,966
    '''
)

# =====================================================
# Task 4: Run dbt Fact (Gold layer)
# =====================================================
task_dbt_fact = BashOperator(
    task_id='dbt_fact',
    bash_command='''
    export DBT_LOG_PATH=/tmp && cd /opt/dbt && dbt run --select fact_sales --profiles-dir . --target dev --no-version-check --target-path /tmp/dbt_target 2>&1
    ''',
    dag=dag,
    doc='''
    **Task**: Aggregate Silver → Gold (Facts)
    - Model: fact_sales
    - Schema: gold.mart
    - Location: s3a://gold/warehouse/mart/
    - Aggregation: GROUP BY month_key, site, product_id
    - Expected rows: ~703,824
    '''
)

# =====================================================
# Task 5: Data Quality Tests
# =====================================================
task_dbt_test = BashOperator(
    task_id='dbt_tests',
    bash_command='''
    export DBT_LOG_PATH=/tmp && cd /opt/dbt && dbt test --profiles-dir . --target dev --no-version-check --target-path /tmp/dbt_target 2>&1
    ''',
    trigger_rule='all_done',  # Run even if previous tasks fail
    dag=dag,
    doc='''
    **Task**: Validate data quality
    - NOT NULL checks on critical columns
    - Range checks (no negative values)
    - Expected: All tests pass
    '''
)

# =====================================================
# Task 6: Success Notification
# =====================================================
task_success = PythonOperator(
    task_id='success_notification',
    python_callable=success_notification,
    provide_context=True,
    dag=dag,
    doc='Notify on successful pipeline completion'
)

# =====================================================
# Task Dependencies (Execution Order)
# =====================================================
# Sequential pipeline: ingest → staging → fact → tests → success
task_ingest_bronze >> task_dbt_staging >> task_dbt_fact >> task_dbt_test >> task_success

# Alternative (if you want staging & facts in parallel):
# task_ingest_bronze >> task_dbt_deps >> [task_dbt_staging, task_dbt_fact] >> task_dbt_test >> task_success
