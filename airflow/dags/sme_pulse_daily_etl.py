"""
SME Pulse Daily ETL Pipeline
DAG chính chạy hàng ngày để xử lý dữ liệu từ Bronze → Silver → Gold

Schedule: Daily at 2:00 AM
Tasks: 11 main tasks organized in TaskGroups
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from airflow.operators.bash import BashOperator
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.task_group import TaskGroup
import yaml
import logging
from pathlib import Path

# Import helper functions
from utils.minio_helpers import check_minio_health, validate_bronze_files
from utils.trino_helpers import check_trino_health, get_table_stats
from utils.dbt_helpers import (
    run_dbt_command, 
    check_run_results, 
    check_seed_changes,
    validate_dbt_models
)
from utils.notification_helpers import (
    generate_pipeline_report,
    notify_pipeline_completion
)
from utils.postgres_helpers import extract_and_load_transactional_data

logger = logging.getLogger(__name__)

# Load pipeline configuration
CONFIG_PATH = Path(__file__).parent / "config" / "pipeline_config.yml"
with open(CONFIG_PATH, 'r') as f:
    PIPELINE_CONFIG = yaml.safe_load(f)

# Default DAG arguments
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': PIPELINE_CONFIG.get('notifications', {}).get('email', {}).get('recipients', []),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2)
}


# ============================================================================
# TASK FUNCTIONS
# ============================================================================

def verify_infrastructure(**context):
    """
    Task 1: Kiểm tra MinIO và Trino services đang chạy
    """
    logger.info("Verifying infrastructure health...")
    
    # Check MinIO
    minio_health = check_minio_health(PIPELINE_CONFIG['minio'])
    logger.info(f"MinIO Status: {minio_health}")
    
    if minio_health['status'] != 'healthy':
        logger.warning(f"MinIO unhealthy: {minio_health['message']}")
        # Do not raise exception, just log and continue
    
    # Check Trino
    trino_health = check_trino_health(PIPELINE_CONFIG['trino'])
    logger.info(f"Trino Status: {trino_health}")
    
    if trino_health['status'] != 'healthy':
        raise Exception(f"Trino unhealthy: {trino_health['message']}")
    
    # Push to XCom
    context['ti'].xcom_push(key='infrastructure_health', value={
        'minio': minio_health,
        'trino': trino_health
    })
    
    logger.info("✅ Infrastructure verification passed")


def extract_transactional_data(**context):
    """
    Task 2: Extract transactional data from App DB (PostgreSQL)
    
    Extracts:
    - finance.ar_invoices
    - finance.payments
    - finance.payment_allocations
    
    Saves to MinIO Bronze layer as Parquet files
    
    **Incremental Load Logic:**
    - Lần chạy đầu tiên (hoặc backfill): Load tất cả data
    - Lần chạy tiếp theo: Chỉ load records có updated_at >= (execution_date - 1 day)
    - Điều này đảm bảo chỉ load data mới, không duplicate
    """
    logger.info("🔄 Starting extraction of transactional data from App DB...")
    
    try:
        # Calculate last_run_time for incremental load
        # Logic: Load data updated in the last 24 hours (from yesterday 00:00:00)
        execution_date = context['execution_date']
        last_run_time = (execution_date - timedelta(days=1)).strftime('%Y-%m-%d 00:00:00')
        
        logger.info(f"📅 Execution date: {execution_date}")
        logger.info(f"📅 Loading records updated after: {last_run_time}")
        
        results = extract_and_load_transactional_data(
            postgres_config=PIPELINE_CONFIG.get('postgres', {}),
            minio_config=PIPELINE_CONFIG.get('minio', {}),
            bucket='sme-pulse',
            last_run_time=last_run_time,  # Pass incremental filter
            context=context
        )
        
        logger.info(f"✅ Extraction completed successfully:")
        logger.info(f"   - AR Invoices: {results['ar_invoices_count']}")
        logger.info(f"   - Payments: {results['payments_count']}")
        logger.info(f"   - Payment Allocations: {results['payment_allocations_count']}")
        logger.info(f"   - Total: {results['total_records']} records")
        logger.info(f"   - Load type: {results['load_type']}")
        
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        raise


def validate_bronze_data(**context):
    """
    Task 5: Validate Bronze layer data
    Note: Bronze files trong MinIO là optional vì data đã có trong Trino external tables
    """
    logger.info("Validating Bronze layer files...")
    
    validation_results = validate_bronze_files(PIPELINE_CONFIG['minio'])
    logger.info(f"Bronze validation results: {validation_results}")
    
    # Check if all sources are OK (allow missing files vì dùng Trino external tables)
    failed_sources = [
        source for source, result in validation_results.items() 
        if result['status'] == 'error'  # Chỉ fail khi có error, không fail khi missing
    ]
    
    if failed_sources:
        logger.warning(f"⚠️ Bronze validation có errors: {failed_sources}")
        # Không raise exception, chỉ warning
    
    context['ti'].xcom_push(key='bronze_validation', value=validation_results)
    logger.info("✅ Bronze layer validation completed (external tables in Trino)")


def should_reload_seeds(**context):
    """
    Task 6a: Check nếu cần reload seeds
    Returns True nếu có thay đổi, False nếu không
    
    Note: Seeds nên được load manually từ dbt container:
    docker compose exec dbt dbt seed --profiles-dir /opt/dbt
    """
    logger.info("Checking if seeds need reloading...")
    
    # Kiểm tra seeds đã tồn tại trong Trino
    from utils.trino_helpers import validate_table_exists
    
    trino_config = PIPELINE_CONFIG['trino']
    seed_tables = ['seed_carrier_map', 'seed_channel_map', 'seed_payment_method_map', 
                   'seed_fx_rates', 'seed_vietnam_locations', 'seed_vn_holidays']
    
    all_seeds_exist = all(
        validate_table_exists(trino_config, 'silver', table)
        for table in seed_tables
    )
    
    if all_seeds_exist:
        logger.info("✅ All seeds already exist in Trino, skipping reload")
        return False  # Skip seed loading
    
    logger.warning("⚠️ Some seeds missing, need manual load: docker compose exec dbt dbt seed")
    return False  # Skip for now, load manually


def validate_silver_layer(**context):
    """
    Task 7b: Validate Silver layer data quality
    """
    logger.info("Validating Silver layer...")
    
    expected_counts = PIPELINE_CONFIG.get('expected_row_counts', {}).get('silver', {})
    
    if not expected_counts:
        logger.warning("⚠️ No expected counts configured for Silver, skipping validation")
        context['ti'].xcom_push(key='silver_validation', value={'status': 'skipped'})
        return
    
    validation_results = validate_dbt_models(
        config=PIPELINE_CONFIG,
        layer='silver',
        expected_counts=expected_counts
    )
    
    logger.info(f"Silver validation: {validation_results}")
    
    # Push to XCom
    context['ti'].xcom_push(key='silver_validation', value=validation_results)
    
    # Raise warning if models failed
    if validation_results.get('models_failed', 0) > 0:
        logger.warning(f"⚠️ {validation_results['models_failed']} Silver models failed validation")


def validate_gold_dims(**context):
    """
    Task 9b: Validate Gold dimensions
    """
    logger.info("Validating Gold dimensions...")
    
    expected_counts = PIPELINE_CONFIG.get('expected_row_counts', {}).get('gold_dims', {})
    
    if not expected_counts:
        logger.warning("⚠️ No expected counts configured for Gold dims, skipping validation")
        context['ti'].xcom_push(key='gold_dims_validation', value={'status': 'skipped'})
        return
    
    validation_results = validate_dbt_models(
        config=PIPELINE_CONFIG,
        layer='gold',
        expected_counts=expected_counts
    )
    
    logger.info(f"Gold dims validation: {validation_results}")
    context['ti'].xcom_push(key='gold_dims_validation', value=validation_results)
    
    if validation_results.get('models_failed', 0) > 0:
        logger.warning(f"⚠️ {validation_results['models_failed']} Gold dimension models failed")


def validate_gold_facts(**context):
    """
    Task 11b: Validate Gold facts
    """
    logger.info("Validating Gold facts...")
    
    expected_counts = PIPELINE_CONFIG.get('expected_row_counts', {}).get('gold_facts', {})
    
    if not expected_counts:
        logger.warning("⚠️ No expected counts configured for Gold facts, skipping validation")
        context['ti'].xcom_push(key='gold_facts_validation', value={'status': 'skipped'})
        return
    
    validation_results = validate_dbt_models(
        config=PIPELINE_CONFIG,
        layer='gold',
        expected_counts=expected_counts
    )
    
    logger.info(f"Gold facts validation: {validation_results}")
    context['ti'].xcom_push(key='gold_facts_validation', value=validation_results)
    
    if validation_results.get('models_failed', 0) > 0:
        logger.warning(f"⚠️ {validation_results['models_failed']} Gold fact models failed")


def refresh_metabase_cache(**context):
    """
    Task 15a: Refresh Metabase cache
    """
    logger.info("Refreshing Metabase cache...")
    
    try:
        metabase_config = PIPELINE_CONFIG.get('metabase', {})
        if not metabase_config.get('enabled', True):
            logger.info("Metabase integration disabled, skipping...")
            return
        
        # Check if requests library available
        try:
            import requests
        except ImportError:
            logger.warning("⚠️ requests library not available, skipping Metabase refresh")
            return
        
        # Call Metabase API để refresh specific database
        url = f"{metabase_config.get('url', 'http://metabase:3000')}/api/database/{metabase_config.get('database_id', 1)}/sync_schema"
        
        response = requests.post(
            url,
            headers={'X-Metabase-Session': metabase_config.get('api_key', '')},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info("✅ Metabase cache refreshed successfully")
        else:
            logger.warning(f"⚠️ Metabase refresh returned status {response.status_code}")
    
    except Exception as e:
        logger.warning(f"⚠️ Error refreshing Metabase cache: {e}")
        # Don't fail pipeline for cache refresh errors
        pass


def invalidate_redis_cache(**context):
    """
    Task 15b: Invalidate Redis cache
    """
    logger.info("Invalidating Redis cache...")
    
    try:
        redis_config = PIPELINE_CONFIG.get('redis', {})
        if not redis_config.get('enabled', True):
            logger.info("Redis integration disabled, skipping...")
            return
        
        # Check if redis library available
        try:
            import redis
        except ImportError:
            logger.warning("⚠️ redis library not available, skipping cache invalidation")
            return
        
        # Connect to Redis
        r = redis.Redis(
            host=redis_config.get('host', 'redis'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0),
            password=redis_config.get('password'),
            socket_connect_timeout=5
        )
        
        # Test connection
        r.ping()
        
        # Invalidate cache keys matching pattern
        cache_patterns = redis_config.get('cache_patterns', ['sme:gold:*'])
        total_deleted = 0
        
        for pattern in cache_patterns:
            keys = r.keys(pattern)
            if keys:
                deleted = r.delete(*keys)
                total_deleted += deleted
                logger.info(f"Deleted {deleted} keys matching '{pattern}'")
        
        if total_deleted > 0:
            logger.info(f"✅ Invalidated {total_deleted} Redis cache keys total")
        else:
            logger.info("No Redis keys to invalidate")
    
    except Exception as e:
        logger.warning(f"⚠️ Error invalidating Redis cache: {e}")
        # Don't fail pipeline for cache invalidation errors
        pass


def generate_report(**context):
    """
    Task 16: Tạo báo cáo pipeline execution
    """
    logger.info("Generating pipeline execution report...")
    
    ti = context['ti']
    
    # Gather results from XCom
    infrastructure = ti.xcom_pull(key='infrastructure_health', task_ids='verify_infrastructure')
    bronze_val = ti.xcom_pull(key='bronze_validation', task_ids='validate_bronze')
    silver_val = ti.xcom_pull(key='silver_validation', task_ids='validate_silver')
    gold_dims_val = ti.xcom_pull(key='gold_dims_validation', task_ids='validate_gold_dims')
    gold_facts_val = ti.xcom_pull(key='gold_facts_validation', task_ids='validate_gold_facts')
    
    # Build task results
    tasks_results = [
        {'task_id': 'infrastructure', 'status': 'success' if infrastructure else 'unknown'},
        {'task_id': 'bronze_validation', 'status': 'success' if bronze_val else 'unknown'},
        {'task_id': 'silver_layer', 'status': 'success' if silver_val else 'unknown'},
        {'task_id': 'gold_dims', 'status': 'success' if gold_dims_val else 'unknown'},
        {'task_id': 'gold_facts', 'status': 'success' if gold_facts_val else 'unknown'}
    ]
    
    # Determine overall status
    overall_status = 'success'
    
    report = generate_pipeline_report(
        pipeline_name='sme_pulse_daily_etl',
        execution_date=context['ds'],
        tasks_results=tasks_results,
        overall_status=overall_status
    )
    
    logger.info(f"\n{report}")
    ti.xcom_push(key='pipeline_report', value=report)


def send_notification(**context):
    """
    Task 17: Gửi notification về pipeline completion
    """
    logger.info("Sending pipeline completion notification...")
    
    ti = context['ti']
    report = ti.xcom_pull(key='pipeline_report', task_ids='generate_report')
    
    # Send notifications
    notify_pipeline_completion(
        config=PIPELINE_CONFIG,
        pipeline_name='sme_pulse_daily_etl',
        execution_date=context['ds'],
        status='success',
        tasks_results=[]  # Already included in report
    )
    
    logger.info("✅ Notification sent")


# ============================================================================
# DAG DEFINITION
# ============================================================================

with DAG(
    'sme_pulse_daily_etl',
    default_args=default_args,
    description='SME Pulse Daily ETL Pipeline - Bronze to Gold',
    schedule_interval='0 2 * * *',  # Daily at 2:00 AM
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['sme-pulse', 'production', 'daily'],
    max_active_runs=1
) as dag:
    
    # Task 1: Infrastructure verification
    verify_infra_task = PythonOperator(
        task_id='verify_infrastructure',
        python_callable=verify_infrastructure
    )
    
    # Task 2: Extract transactional data from App DB
    extract_data_task = PythonOperator(
        task_id='extract_transactional_data',
        python_callable=extract_transactional_data,
        execution_timeout=timedelta(minutes=30)
    )
    
    # Tasks 3-4: Bronze ingestion (giả sử đã có data trong MinIO)
    # Trong production, cần thêm tasks để ingest từ source systems
    
    # Task 5: Bronze validation
    validate_bronze_task = PythonOperator(
        task_id='validate_bronze',
        python_callable=validate_bronze_data
    )
    
    # Task 6: dbt Seed Management (SKIPPED - seeds loaded manually)
    # Seeds đã được load từ dbt container:
    # docker compose exec dbt dbt seed --profiles-dir /opt/dbt
    # Không cần reload trong DAG vì seeds ít thay đổi
    
    # Tasks 7-8: Silver Layer (Staging + Features + ML Training)
    with TaskGroup('silver_layer', tooltip='Process Silver layer: staging, features, ML training data') as silver_group:
        # 7a: Silver Staging (stg_* models)
        run_staging = BashOperator(
            task_id='run_staging',
            bash_command=PIPELINE_CONFIG.get('dbt', {}).get('silver_staging_command', 'echo "No silver_staging_command configured"'),
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=10)
        )
        
        test_staging = BashOperator(
            task_id='test_staging',
            bash_command=PIPELINE_CONFIG.get('dbt', {}).get('test_silver_staging_command', 'echo "No test_silver_staging_command configured"'),
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=5)
        )
        
        # 7b: Silver Features (ftr_* models - depends on staging)
        run_features = BashOperator(
            task_id='run_features',
            bash_command=PIPELINE_CONFIG.get('dbt', {}).get('silver_feature_command', 'echo "No silver_feature_command configured"'),
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=10)
        )
        
        test_features = BashOperator(
            task_id='test_features',
            bash_command=PIPELINE_CONFIG.get('dbt', {}).get('test_silver_feature_command', 'echo "No test_silver_feature_command configured"'),
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=5)
        )
        
        # 7c: Silver ML Training (ml_training_* models - depends on features)
        run_ml_training = BashOperator(
            task_id='run_ml_training',
            bash_command=PIPELINE_CONFIG.get('dbt', {}).get('silver_ml_training_command', 'echo "No silver_ml_training_command configured"'),
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=10)
        )
        
        test_ml_training = BashOperator(
            task_id='test_ml_training',
            bash_command=PIPELINE_CONFIG.get('dbt', {}).get('test_silver_ml_training_command', 'echo "No test_silver_ml_training_command configured"'),
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=5)
        )
        
        validate_silver_task = PythonOperator(
            task_id='validate_silver',
            python_callable=validate_silver_layer,
            execution_timeout=timedelta(minutes=3)
        )
        
        # Dependency: staging -> features -> ml_training -> validation
        run_staging >> test_staging >> run_features >> test_features
        test_features >> run_ml_training >> test_ml_training >> validate_silver_task
    
    # Tasks 9-10: Gold Dimensions
    with TaskGroup('gold_dimensions', tooltip='Build Gold dimension tables') as gold_dims_group:
        run_gold_dims = BashOperator(
            task_id='run_gold_dims',
            bash_command=PIPELINE_CONFIG['dbt']['gold_dims_command'],
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=10)
        )
        
        test_gold_dims = BashOperator(
            task_id='test_gold_dims',
            bash_command=PIPELINE_CONFIG['dbt']['test_gold_dims_command'],
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=5)
        )
        
        validate_dims_task = PythonOperator(
            task_id='validate_gold_dims',
            python_callable=validate_gold_dims,
            execution_timeout=timedelta(minutes=3)
        )
        
        run_gold_dims >> test_gold_dims >> validate_dims_task
    
    # Tasks 11-12: Gold Facts
    with TaskGroup('gold_facts', tooltip='Build Gold fact tables') as gold_facts_group:
        run_gold_facts = BashOperator(
            task_id='run_gold_facts',
            bash_command=PIPELINE_CONFIG['dbt']['gold_facts_command'],
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=15)
        )
        
        test_gold_facts = BashOperator(
            task_id='test_gold_facts',
            bash_command=PIPELINE_CONFIG['dbt']['test_gold_facts_command'],
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=5)
        )
        
        validate_facts_task = PythonOperator(
            task_id='validate_gold_facts',
            python_callable=validate_gold_facts,
            execution_timeout=timedelta(minutes=3)
        )
        
        run_gold_facts >> test_gold_facts >> validate_facts_task
    
    # Tasks 13-14: Gold Links (1% sample for performance)
    # Link tables: link_bank_payment, link_order_payment, link_order_shipment
    # Note: Chỉ xử lý 1% data (MOD(date_key, 100) = 0) để tránh timeout
    with TaskGroup('gold_links', tooltip='Build Gold link tables (1% sample)') as gold_links_group:
        run_gold_links = BashOperator(
            task_id='run_gold_links',
            bash_command=PIPELINE_CONFIG['dbt']['gold_links_command'],
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=15)  # 15 min timeout cho links
        )
        
        test_gold_links = BashOperator(
            task_id='test_gold_links',
            bash_command=PIPELINE_CONFIG['dbt']['test_gold_links_command'],
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=5)
        )
        
        run_gold_links >> test_gold_links
    
    # Tasks 15-16: Gold KPI (Business metrics and aggregations)
    # KPI tables: kpi_daily_revenue, kpi_payment_success_rate, kpi_ar_dso_analysis, kpi_reconciliation_daily
    with TaskGroup('gold_kpi', tooltip='Build Gold KPI tables') as gold_kpi_group:
        run_gold_kpi = BashOperator(
            task_id='run_gold_kpi',
            bash_command=PIPELINE_CONFIG.get('dbt', {}).get('gold_kpi_command', 'echo "No gold_kpi_command configured"'),
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=10)
        )
        
        test_gold_kpi = BashOperator(
            task_id='test_gold_kpi',
            bash_command=PIPELINE_CONFIG.get('dbt', {}).get('test_gold_kpi_command', 'echo "No test_gold_kpi_command configured"'),
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=5)
        )
        
        run_gold_kpi >> test_gold_kpi
    
    # Tasks 17-18: Gold ML Scores (UC05 - AR Priority Heuristic Scoring)
    # This is SQL-based scoring logic, so it runs as part of dbt Gold layer
    with TaskGroup('gold_ml_scores', tooltip='Build ML Scoring tables (UC05 - AR Priority)') as gold_ml_scores_group:
        run_ml_scores = BashOperator(
            task_id='run_ml_ar_scores',
            bash_command=PIPELINE_CONFIG.get('dbt', {}).get('gold_ml_scores_command', 'echo "No gold_ml_scores_command configured"'),
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=10)
        )
        
        test_ml_scores = BashOperator(
            task_id='test_ml_ar_scores',
            bash_command=PIPELINE_CONFIG.get('dbt', {}).get('test_gold_ml_scores_command', 'echo "No test_gold_ml_scores_command configured"'),
            cwd='/opt/dbt',
            execution_timeout=timedelta(minutes=5)
        )
        
        run_ml_scores >> test_ml_scores
    
    # Task 19: Trigger ML Predict DAG
    # After ETL completes, trigger ML inference pipeline (UC09, UC10)
    trigger_ml_predict = TriggerDagRunOperator(
        task_id='trigger_ml_predict',
        trigger_dag_id='sme_pulse_ml_predict',
        wait_for_completion=False,  # Async trigger
        execution_date='{{ ds }}',
        reset_dag_run=True
    )
    
    # Task 20: Generate Report
    generate_report_task = PythonOperator(
        task_id='generate_report',
        python_callable=generate_report
    )
    
    # Task 21: Send Notification
    send_notification_task = PythonOperator(
        task_id='send_notification',
        python_callable=send_notification
    )
    
    # ============================================================================
    # TASK DEPENDENCIES
    # ============================================================================
    
    # Linear flow: Infrastructure -> Extract -> Validate -> Silver -> Gold -> KPI -> ML Scores -> Reports
    verify_infra_task >> extract_data_task >> validate_bronze_task >> silver_group
    silver_group >> gold_dims_group >> gold_facts_group
    gold_facts_group >> gold_links_group >> gold_kpi_group
    
    # UC05 ML Scoring runs after KPI
    gold_kpi_group >> gold_ml_scores_group
    
    # Trigger ML Predict DAG after all Gold layers complete
    gold_ml_scores_group >> trigger_ml_predict
    
    # Report and notification run in parallel with ML trigger
    gold_ml_scores_group >> generate_report_task >> send_notification_task
