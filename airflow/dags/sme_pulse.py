"""
===================================================
SME Pulse - Main Data Pipeline DAG
===================================================
Mục đích: Điều phối toàn bộ ELT pipeline
Schedule: Chạy mỗi giờ
Flow: Ingest → DQ → Transform Silver → DQ → Transform Gold → Cache Invalidation
===================================================
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import subprocess

# ===== DEFAULT ARGS =====
default_args = {
    'owner': 'sme-pulse',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# ===== DAG DEFINITION =====
with DAG(
    dag_id='sme_pulse_pipeline',
    default_args=default_args,
    description='ELT pipeline cho SME Pulse - POS/Payments/Shipments/Bank',
    schedule_interval='@hourly',  # Chạy mỗi giờ
    start_date=datetime(2025, 10, 1),
    catchup=False,  # Không chạy lại các lần bị missed
    tags=['sme-pulse', 'elt', 'production'],
) as dag:

    # ===== TASK 1: INGEST DATA =====
    # Placeholder: Trong thực tế sẽ gọi Airbyte API hoặc custom ingestion script
    ingest_pos = BashOperator(
        task_id='ingest_pos_data',
        bash_command='echo "📥 Ingest POS data from API/CSV - Placeholder"',
    )

    # ===== TASK 2: DATA QUALITY CHECK - BRONZE LAYER =====
    dq_bronze = BashOperator(
        task_id='dq_check_bronze',
        bash_command='''
        echo "🔍 Data Quality Check - Bronze Layer"
        echo "Kiểm tra: null values, schema validation, duplicate event_id"
        echo "Tool: Great Expectations (placeholder)"
        ''',
    )

    # ===== TASK 3: DBT RUN - SILVER LAYER =====
    dbt_silver = BashOperator(
        task_id='dbt_transform_silver',
        bash_command='''
        cd /opt/dbt && \
        dbt deps && \
        dbt run --select silver.stg_transactions --profiles-dir /opt/dbt
        ''',
    )

    # ===== TASK 4: DATA QUALITY CHECK - SILVER LAYER =====
    dq_silver = BashOperator(
        task_id='dq_check_silver',
        bash_command='''
        echo "🔍 Data Quality Check - Silver Layer"
        echo "Kiểm tra: business rules, metric ranges"
        cd /opt/dbt && dbt test --select silver.stg_transactions --profiles-dir /opt/dbt
        ''',
    )

    # ===== TASK 5: DBT RUN - GOLD LAYER =====
    dbt_gold = BashOperator(
        task_id='dbt_transform_gold',
        bash_command='''
        cd /opt/dbt && \
        dbt run --select gold.fact_orders --profiles-dir /opt/dbt
        ''',
    )

    # ===== TASK 6: INVALIDATE REDIS CACHE =====
    def invalidate_cache():
        """
        Invalidate Redis cache sau khi gold tables được refresh
        Trong production: xóa keys matching pattern v1:*:cash:*
        """
        print("🗑️  Invalidating Redis cache...")
        print("Pattern: v1:*:cash:overview, v1:*:revenue:*")
        # Placeholder - trong thực tế sẽ gọi Redis
        # redis_client.delete('v1:org-sme-001:cash:overview')
        print("✅ Cache invalidated successfully!")

    invalidate = PythonOperator(
        task_id='invalidate_redis_cache',
        python_callable=invalidate_cache,
    )

    # ===== TASK 7: NOTIFY SUCCESS =====
    notify_success = BashOperator(
        task_id='notify_success',
        bash_command='''
        echo "✨ Pipeline hoàn thành!"
        echo "Thời gian: $(date)"
        echo "Có thể kiểm tra kết quả tại Metabase: http://localhost:3000"
        ''',
    )

    # ===== DEFINE TASK DEPENDENCIES =====
    # Luồng tuần tự: Ingest → DQ → Silver → DQ → Gold → Invalidate → Notify
    ingest_pos >> dq_bronze >> dbt_silver >> dq_silver >> dbt_gold >> invalidate >> notify_success
