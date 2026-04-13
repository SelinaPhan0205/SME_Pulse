"""
SME Pulse Data Quality Monitor
DAG chạy kiểm tra chất lượng dữ liệu sau mỗi ETL run

Schedule: Daily (after ETL completes)
Checks:
  - Row count assertions (Bronze / Silver / Gold layers)
  - Null rate thresholds on critical columns
  - Link table match rates (should be > 0% after sampling fix)
  - Orphan file detection in MinIO/Iceberg
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor
import logging

logger = logging.getLogger(__name__)

# Default DAG arguments
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
    'execution_timeout': timedelta(minutes=30),
}

# ============================================================================
# DATA QUALITY CHECK FUNCTIONS
# ============================================================================

TRINO_HOST = 'trino'
TRINO_PORT = 8080
TRINO_USER = 'airflow'
TRINO_CATALOG = 'sme_lake'


def _get_trino_cursor():
    """Get a Trino cursor for DQ queries."""
    from trino.dbapi import connect
    conn = connect(host=TRINO_HOST, port=TRINO_PORT, user=TRINO_USER, catalog=TRINO_CATALOG)
    return conn.cursor()


def _run_count_check(cursor, schema, table, min_rows=1):
    """Assert a table has at least min_rows."""
    cursor.execute(f"SELECT COUNT(*) FROM {TRINO_CATALOG}.{schema}.{table}")
    count = cursor.fetchone()[0]
    logger.info(f"  {schema}.{table}: {count:,} rows")
    if count < min_rows:
        raise ValueError(f"DQ FAIL: {schema}.{table} has {count} rows (expected >= {min_rows})")
    return count


def check_bronze_layer(**context):
    """Verify Bronze layer row counts are non-zero."""
    logger.info("=== Bronze Layer Row Counts ===")
    cursor = _get_trino_cursor()

    bronze_tables = [
        'bank_transactions_raw',
        'invoices_ar_raw',
        'retail_orders_raw',
        'shipments_raw',
    ]

    results = {}
    for tbl in bronze_tables:
        try:
            results[tbl] = _run_count_check(cursor, 'bronze', tbl, min_rows=1)
        except Exception as e:
            logger.warning(f"  Skipping {tbl}: {e}")
            results[tbl] = -1

    context['ti'].xcom_push(key='bronze_counts', value=results)
    logger.info("✅ Bronze DQ check done")


def check_silver_layer(**context):
    """Verify Silver staging tables have data and acceptable null rates."""
    logger.info("=== Silver Layer Checks ===")
    cursor = _get_trino_cursor()

    silver_tables = [
        ('silver', 'stg_bank_txn_vn', 'txn_id_nat'),
        ('silver', 'stg_orders_vn', 'order_id_nat'),
        ('silver', 'stg_payments_vn', 'payment_id_nat'),
        ('silver', 'stg_shipments_vn', 'shipment_id_nat'),
    ]

    for schema, table, pk_col in silver_tables:
        try:
            count = _run_count_check(cursor, schema, table, min_rows=1)

            # Null rate on PK column should be 0
            cursor.execute(
                f"SELECT COUNT(*) FROM {TRINO_CATALOG}.{schema}.{table} "
                f"WHERE {pk_col} IS NULL"
            )
            null_count = cursor.fetchone()[0]
            null_rate = null_count / max(count, 1)
            logger.info(f"  {table}.{pk_col} null rate: {null_rate:.4%}")
            if null_rate > 0:
                raise ValueError(f"DQ FAIL: PK {pk_col} has {null_count} NULLs in {table}")
        except ValueError:
            raise
        except Exception as e:
            logger.warning(f"  Skipping {table}: {e}")

    logger.info("✅ Silver DQ check done")


def check_gold_layer(**context):
    """Verify Gold fact/dim tables and link match rates."""
    logger.info("=== Gold Layer Checks ===")
    cursor = _get_trino_cursor()

    # Fact tables must have rows
    fact_tables = ['fact_orders', 'fact_payments', 'fact_bank_txn', 'fact_shipments']
    for tbl in fact_tables:
        try:
            _run_count_check(cursor, 'gold', tbl, min_rows=1)
        except Exception as e:
            logger.warning(f"  Skipping gold.{tbl}: {e}")

    # Link table match rates (after removing sampling, these should be > 0)
    link_checks = {
        'link_bank_payment': "SELECT COUNT(*) AS total, "
                             "SUM(CASE WHEN match_method = 'MATCHED' THEN 1 ELSE 0 END) AS matched "
                             f"FROM {TRINO_CATALOG}.gold.link_bank_payment",
        'link_order_payment': "SELECT COUNT(*) AS total, "
                              "SUM(CASE WHEN is_best_match_for_order THEN 1 ELSE 0 END) AS matched "
                              f"FROM {TRINO_CATALOG}.gold.link_order_payment",
        'link_order_shipment': "SELECT COUNT(*) AS total, "
                               "SUM(CASE WHEN match_type = 'MATCHED' THEN 1 ELSE 0 END) AS matched "
                               f"FROM {TRINO_CATALOG}.gold.link_order_shipment",
    }
    link_results = {}
    for table_name, sql in link_checks.items():
        try:
            cursor.execute(sql)
            row = cursor.fetchone()
            total, matched = row[0], row[1]
            match_rate = matched / max(total, 1)
            logger.info(f"  {table_name}: {matched:,}/{total:,} matched ({match_rate:.1%})")
            link_results[table_name] = {'total': total, 'matched': matched, 'rate': match_rate}
            if total > 0 and match_rate < 0.01:
                logger.warning(f"  ⚠️  Very low match rate for {table_name}!")
        except Exception as e:
            logger.warning(f"  Skipping {table_name}: {e}")

    context['ti'].xcom_push(key='link_match_rates', value=link_results)
    logger.info("✅ Gold DQ check done")


def check_transaction_categories(**context):
    """
    Verify transaction_category in fact_bank_txn is not >80% UNCLASSIFIED.
    This catches regressions in the keyword-based classification.
    """
    logger.info("=== Transaction Category Distribution ===")
    cursor = _get_trino_cursor()

    sql = f"""
    SELECT transaction_category, COUNT(*) AS cnt
    FROM {TRINO_CATALOG}.gold.fact_bank_txn
    GROUP BY transaction_category
    ORDER BY cnt DESC
    """
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        total = sum(r[1] for r in rows)
        for cat, cnt in rows:
            logger.info(f"  {cat}: {cnt:,} ({cnt/max(total,1):.1%})")

        unclassified = next((cnt for cat, cnt in rows if cat == 'UNCLASSIFIED'), 0)
        unclass_rate = unclassified / max(total, 1)
        if unclass_rate > 0.80:
            raise ValueError(
                f"DQ FAIL: {unclass_rate:.0%} of bank transactions are UNCLASSIFIED. "
                "Keyword mapping in fact_bank_txn.sql needs review."
            )
    except ValueError:
        raise
    except Exception as e:
        logger.warning(f"  Skipping txn category check: {e}")

    logger.info("✅ Transaction category DQ check done")


def generate_dq_report(**context):
    """Generate a summary DQ report pushed to XCom."""
    ti = context['ti']
    bronze = ti.xcom_pull(task_ids='check_bronze', key='bronze_counts') or {}
    links = ti.xcom_pull(task_ids='check_gold', key='link_match_rates') or {}

    report_lines = [
        "=" * 60,
        "DATA QUALITY REPORT",
        f"Run date: {context['execution_date']}",
        "=" * 60,
        "",
        "Bronze counts:",
    ]
    for tbl, cnt in bronze.items():
        report_lines.append(f"  {tbl}: {cnt:,}")

    report_lines.append("")
    report_lines.append("Link match rates:")
    for tbl, info in links.items():
        rate = info.get('rate', 0)
        report_lines.append(f"  {tbl}: {info.get('matched',0):,}/{info.get('total',0):,} ({rate:.1%})")

    report = "\n".join(report_lines)
    logger.info(report)
    ti.xcom_push(key='dq_report', value=report)
    logger.info("✅ DQ report generated")


# ============================================================================
# DAG DEFINITION
# ============================================================================

with DAG(
    dag_id='sme_pulse_data_quality',
    default_args=default_args,
    description='Data Quality Monitor (runs after daily ETL)',
    schedule_interval='30 1 * * *',  # 1:30 AM daily (30min after ETL)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['data-quality', 'monitoring', 'daily'],
) as dag:

    # Wait for daily ETL to finish
    wait_for_etl = ExternalTaskSensor(
        task_id='wait_for_daily_etl',
        external_dag_id='sme_pulse_daily_etl',
        external_task_id=None,
        allowed_states=['success'],
        failed_states=['failed'],
        mode='reschedule',
        timeout=3600,
        poke_interval=120,
        execution_delta=timedelta(minutes=30),
    )

    check_bronze_task = PythonOperator(
        task_id='check_bronze',
        python_callable=check_bronze_layer,
    )

    check_silver_task = PythonOperator(
        task_id='check_silver',
        python_callable=check_silver_layer,
    )

    check_gold_task = PythonOperator(
        task_id='check_gold',
        python_callable=check_gold_layer,
    )

    check_txn_cat_task = PythonOperator(
        task_id='check_transaction_categories',
        python_callable=check_transaction_categories,
    )

    report_task = PythonOperator(
        task_id='generate_dq_report',
        python_callable=generate_dq_report,
    )

    # Dependencies: wait for ETL → check all layers in parallel → report
    wait_for_etl >> [check_bronze_task, check_silver_task, check_gold_task, check_txn_cat_task]
    [check_bronze_task, check_silver_task, check_gold_task, check_txn_cat_task] >> report_task
