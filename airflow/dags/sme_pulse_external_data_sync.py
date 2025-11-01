"""
SME Pulse - External Data Sync DAG
===================================
Monthly orchestration for external macro data sources:
- World Bank Open Data API (Inflation, GDP Growth, Unemployment)
- Vietnam Provinces/Districts API (Geographic hierarchy)

Flow:
1. Ingest World Bank indicators → MinIO (bronze/raw/world_bank/)
2. Ingest Vietnam provinces/districts → MinIO (bronze/raw/vietnam_provinces/)
3. dbt Silver: Transform to staging models (silver.external.*)
4. dbt Gold: Create dimension tables (gold.external.*)
5. dbt Test: Data quality validation

Schedule: Monthly (1st day of month at 00:00 UTC)
"""
from __future__ import annotations
import os
import sys
import importlib.util
from datetime import datetime, timedelta

from airflow.decorators import dag, task_group
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# ====== Environment Variables ======
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
LAKEHOUSE_BUCKET = os.getenv("LAKEHOUSE_BUCKET", "sme-lake")

# External data ingest scripts
OPS_DIR = os.getenv("OPS_DIR", "/opt/ops/external_sources")
WORLD_BANK_SCRIPT = os.path.join(OPS_DIR, "ingest_world_bank.py")
PROVINCES_SCRIPT = os.path.join(OPS_DIR, "ingest_provinces.py")

# dbt configuration
DBT_DIR = os.getenv("DBT_DIR", "/opt/dbt")

# World Bank API configuration
WB_INDICATORS = [
    "FP.CPI.TOTL.ZG",      # Inflation (annual %)
    "NY.GDP.MKTP.KD.ZG",   # GDP growth (annual %)
    "SL.UEM.TOTL.ZS"       # Unemployment rate (%)
]
WB_COUNTRY = "VNM"  # Vietnam
WB_START_YEAR = 2015

# Vietnam Provinces API
PROVINCES_API_URL = "https://provinces.open-api.vn/api/?depth=1"

DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
}


# ====== Helper Functions ======
def _run_python_script(script_path: str, script_name: str):
    """
    Dynamically import and run a Python script's main() function.
    Fallback to subprocess if import fails.
    """
    import logging
    import subprocess
    
    log = logging.getLogger(f"run_{script_name}")
    
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script not found: {script_path}")
    
    log.info(f"📝 Running script: {script_path}")
    
    try:
        # Try to import and run main()
        spec = importlib.util.spec_from_file_location(script_name, script_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            
            if hasattr(mod, "main") and callable(mod.main):
                log.info(f"✅ Calling main() in {script_name}")
                mod.main()
                return
            else:
                log.warning(f"⚠️ No main() function found in {script_name}, trying subprocess")
    except Exception as e:
        log.warning(f"⚠️ Import failed ({e}), falling back to subprocess")
    
    # Fallback: subprocess
    log.info(f"🔧 Running via subprocess: python {script_path}")
    result = subprocess.run(
        [sys.executable, script_path],
        check=True,
        capture_output=True,
        text=True
    )
    log.info(f"✅ Script output:\n{result.stdout}")
    if result.stderr:
        log.warning(f"⚠️ Script stderr:\n{result.stderr}")


def _ingest_world_bank():
    """Ingest World Bank indicators for Vietnam"""
    _run_python_script(WORLD_BANK_SCRIPT, "ingest_world_bank")


def _ingest_provinces():
    """Ingest Vietnam provinces and districts"""
    _run_python_script(PROVINCES_SCRIPT, "ingest_provinces")


def _verify_external_sources():
    """Verify external data sources are accessible"""
    import logging
    import requests
    from minio import Minio
    
    log = logging.getLogger("verify_external_sources")
    
    # 1. Test World Bank API
    log.info("🌍 Testing World Bank API...")
    wb_url = f"http://api.worldbank.org/v2/country/{WB_COUNTRY}/indicator/{WB_INDICATORS[0]}"
    wb_params = {"format": "json", "per_page": 1}
    wb_response = requests.get(wb_url, params=wb_params, timeout=10)
    wb_response.raise_for_status()
    log.info(f"✅ World Bank API accessible (status: {wb_response.status_code})")
    
    # 2. Test Vietnam Provinces API
    log.info("🇻🇳 Testing Vietnam Provinces API...")
    prov_response = requests.get(PROVINCES_API_URL, timeout=10)
    prov_response.raise_for_status()
    log.info(f"✅ Vietnam Provinces API accessible (status: {prov_response.status_code})")
    
    # 3. Test MinIO connection
    log.info("🗄️ Testing MinIO connection...")
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )
    if not minio_client.bucket_exists(LAKEHOUSE_BUCKET):
        raise RuntimeError(f"Bucket '{LAKEHOUSE_BUCKET}' does not exist in MinIO")
    log.info(f"✅ MinIO bucket '{LAKEHOUSE_BUCKET}' exists")
    
    log.info("🎉 All external sources verified successfully!")
    return True


def _check_data_freshness():
    """
    Check if external data needs refresh (monthly).
    Returns True if data is stale (> 30 days old).
    """
    import logging
    from datetime import datetime, timedelta
    from minio import Minio
    
    log = logging.getLogger("check_data_freshness")
    
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )
    
    # Check World Bank data
    wb_prefix = "bronze/raw/world_bank/indicators/"
    wb_objects = list(minio_client.list_objects(LAKEHOUSE_BUCKET, prefix=wb_prefix))
    
    if not wb_objects:
        log.info("📭 No existing World Bank data found. Refresh needed.")
        return True
    
    # Get latest object timestamp
    latest_obj = max(wb_objects, key=lambda x: x.last_modified)
    age_days = (datetime.now(latest_obj.last_modified.tzinfo) - latest_obj.last_modified).days
    
    log.info(f"📅 Latest World Bank data is {age_days} days old (modified: {latest_obj.last_modified})")
    
    if age_days > 30:
        log.info("⏰ Data is stale (> 30 days). Refresh needed.")
        return True
    else:
        log.info("✅ Data is fresh (< 30 days). Skipping ingest.")
        return False


# ====== DAG Definition ======
@dag(
    dag_id="sme_pulse_external_data_sync",
    description="Monthly sync of external macro data sources (World Bank + Vietnam Provinces) for context enrichment",
    schedule="0 0 1 * *",  # Monthly: 1st day at 00:00 UTC
    start_date=datetime(2025, 11, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["sme-pulse", "external-data", "macro-indicators", "geography"],
    max_active_runs=1,
)
def external_data_sync_pipeline():
    
    # ========== STEP 1: Verification ==========
    verify = PythonOperator(
        task_id="verify_external_sources",
        python_callable=_verify_external_sources,
    )
    
    check_freshness = PythonOperator(
        task_id="check_data_freshness",
        python_callable=_check_data_freshness,
    )
    
    # ========== STEP 2: Ingest External Data ==========
    @task_group(group_id="ingest_external_data")
    def ingest_group():
        ingest_wb = PythonOperator(
            task_id="ingest_world_bank",
            python_callable=_ingest_world_bank,
        )
        
        ingest_prov = PythonOperator(
            task_id="ingest_provinces",
            python_callable=_ingest_provinces,
        )
        
        # Run in parallel
        return [ingest_wb, ingest_prov]
    
    # ========== STEP 3: dbt Silver Layer ==========
    @task_group(group_id="dbt_silver_external")
    def dbt_silver_group():
        run_silver = BashOperator(
            task_id="dbt_run_silver_external",
            bash_command=f"cd {DBT_DIR} && dbt run --select silver.external.*",
        )
        
        test_silver = BashOperator(
            task_id="dbt_test_silver_external",
            bash_command=f"cd {DBT_DIR} && dbt test --select silver.external.*",
        )
        
        run_silver >> test_silver
        return test_silver  # Return last task for dependency chaining
    
    # ========== STEP 4: dbt Gold Layer ==========
    @task_group(group_id="dbt_gold_external")
    def dbt_gold_group():
        run_gold = BashOperator(
            task_id="dbt_run_gold_external",
            bash_command=f"cd {DBT_DIR} && dbt run --select gold.external.*",
        )
        
        test_gold = BashOperator(
            task_id="dbt_test_gold_external",
            bash_command=f"cd {DBT_DIR} && dbt test --select gold.external.*",
        )
        
        run_gold >> test_gold
        return test_gold  # Return last task for dependency chaining
    
    # ========== STEP 5: Data Quality Summary ==========
    def _log_summary():
        import logging
        log = logging.getLogger("data_quality_summary")
        log.info("=" * 60)
        log.info("🎉 EXTERNAL DATA SYNC COMPLETED SUCCESSFULLY")
        log.info("=" * 60)
        log.info("✅ World Bank indicators ingested")
        log.info("✅ Vietnam provinces/districts ingested")
        log.info("✅ Silver staging models built")
        log.info("✅ Gold dimension tables built")
        log.info("✅ All data quality tests passed")
        log.info("=" * 60)
    
    summary = PythonOperator(
        task_id="log_summary",
        python_callable=_log_summary,
    )
    
    # ========== DAG Flow ==========
    verify >> check_freshness >> ingest_group() >> dbt_silver_group() >> dbt_gold_group() >> summary


# Instantiate DAG
dag = external_data_sync_pipeline()
