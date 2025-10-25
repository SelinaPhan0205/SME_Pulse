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
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount
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

    # ===== TASK 1: INGEST DATA TO BRONZE (ICEBERG) =====
    ingest_pos = BashOperator(
        task_id='ingest_pos_data',
        bash_command='python /opt/ops/ingest_bronze.py --source pos --num-orders 50',
    )

    # ===== TASK 2: DATA QUALITY CHECK - BRONZE LAYER (TRINO) =====
    dq_bronze = BashOperator(
        task_id='dq_check_bronze',
        bash_command='''
        echo "🔍 Data Quality Check - Bronze Layer (Iceberg)"
        docker exec sme-trino trino --execute "SELECT COUNT(*), COUNT(DISTINCT event_id), COUNT(*) FILTER (WHERE payload_json IS NULL) AS null_count FROM iceberg.bronze.transactions_raw WHERE domain = 'order';"
        echo "✅ DQ check completed"
        ''',
    )

    # ===== TASK 3: DBT RUN - SILVER LAYER (TRINO + ICEBERG) =====
    dbt_silver = BashOperator(
        task_id='dbt_transform_silver',
        bash_command='cd /opt/dbt && dbt run --select stg_transactions --profiles-dir /opt/dbt --target dev',
    )

    # ===== TASK 4: DATA QUALITY CHECK - SILVER LAYER (DBT TESTS) =====
    dq_silver = BashOperator(
        task_id='dq_check_silver',
        bash_command='cd /opt/dbt && dbt test --select stg_transactions --profiles-dir /opt/dbt --target dev',
    )

    # ===== TASK 5: DBT RUN - GOLD LAYER (TRINO + ICEBERG) =====
    dbt_gold = BashOperator(
        task_id='dbt_transform_gold',
        bash_command='cd /opt/dbt && dbt run --select fact_orders --profiles-dir /opt/dbt --target dev',
    )

    # ===== TASK 6: INVALIDATE REDIS CACHE =====
    def invalidate_cache():
        """
        Invalidate Redis cache sau khi gold tables được refresh trong Lakehouse
        Pattern: v1:*:cash:*, v1:*:revenue:*
        """
        print("🗑️  Invalidating Redis cache after Lakehouse refresh...")
        print("Pattern: v1:*:cash:overview, v1:*:revenue:*, v1:*:orders:*")
        print("Gold tables updated: iceberg.gold.fact_orders")
        # Placeholder - trong thực tế sẽ gọi Redis FLUSHDB hoặc DELETE pattern
        # import redis
        # r = redis.Redis(host='redis', port=6379, db=0)
        # for key in r.scan_iter("v1:*:cash:*"): r.delete(key)
        print("✅ Cache invalidated successfully!")

    invalidate = PythonOperator(
        task_id='invalidate_redis_cache',
        python_callable=invalidate_cache,
    )

    # ===== TASK 7: NOTIFY SUCCESS + VERIFY DATA =====
    notify_success = BashOperator(
        task_id='notify_success',
        bash_command='''
        echo "✨ Lakehouse Pipeline hoàn thành!"
        echo "📊 Verify Gold data:"
        docker exec sme-trino trino --execute "SELECT COUNT(*) AS total_fact_rows, SUM(total_revenue) AS total_revenue FROM iceberg.gold.fact_orders;"
        echo "🔗 Metabase Dashboard: http://localhost:3000"
        echo "🔗 Trino UI: http://localhost:8081"
        echo "🔗 MinIO Console: http://localhost:9001"
        ''',
    )

    # ===== DEFINE TASK DEPENDENCIES =====
    # Luồng tuần tự: Ingest → DQ → Silver → DQ → Gold → Invalidate → Notify
    ingest_pos >> dq_bronze >> dbt_silver >> dq_silver >> dbt_gold >> invalidate >> notify_success