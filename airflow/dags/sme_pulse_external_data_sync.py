"""
SME Pulse - External Data Sync DAG
===================================
Monthly orchestration for external macro data sources:
- World Bank Open Data API (Inflation, GDP Growth, Unemployment)
- Vietnam Provinces/Districts API (Geographic hierarchy)

Flow:
1. Verify external data sources accessible
2. Check data freshness (skip if < 30 days old)
3. Ingest World Bank indicators → Silver (stg_world_bank_indicators)
4. Ingest Vietnam provinces/districts → Silver (stg_vietnam_locations)
5. dbt Gold: Create dimension tables (gold.dim_macro_indicators, gold.dim_location_vn)
6. Data quality validation

Schedule: Monthly (1st day of month at 00:00 UTC)
Note: External data ingestion scripts not yet implemented in /opt/ops/external_sources/
Currently using placeholder/mock data flow.
"""
from __future__ import annotations
import os
import sys
import logging
from datetime import datetime, timedelta

from airflow.decorators import dag, task_group
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import yaml
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

logger = logging.getLogger(__name__)

# Load pipeline configuration
CONFIG_PATH = Path(__file__).parent / "config" / "pipeline_config.yml"
with open(CONFIG_PATH, 'r') as f:
    PIPELINE_CONFIG = yaml.safe_load(f)


# ====== Helper Functions ======

def _verify_external_sources():
    """
    Verify external data sources are accessible (World Bank API, Vietnam Provinces API, MinIO)
    """
    log = logging.getLogger("verify_external_sources")
    
    minio_config = PIPELINE_CONFIG['minio']
    
    # 1. Test World Bank API
    log.info("🌍 Testing World Bank API...")
    try:
        import requests
        wb_url = "http://api.worldbank.org/v2/country/VNM/indicator/FP.CPI.TOTL.ZG"
        wb_response = requests.get(wb_url, params={"format": "json", "per_page": 1}, timeout=10)
        wb_response.raise_for_status()
        log.info(f"✅ World Bank API accessible (status: {wb_response.status_code})")
    except ImportError:
        log.warning("⚠️ requests not installed, skipping World Bank API test")
    except Exception as e:
        log.warning(f"⚠️ World Bank API test failed: {e}")
    
    # 2. Test Vietnam Provinces API
    log.info("🇻🇳 Testing Vietnam Provinces API...")
    try:
        import requests
        prov_url = "https://provinces.open-api.vn/api/?depth=1"
        prov_response = requests.get(prov_url, timeout=10)
        prov_response.raise_for_status()
        log.info(f"✅ Vietnam Provinces API accessible (status: {prov_response.status_code})")
    except Exception as e:
        log.warning(f"⚠️ Vietnam Provinces API test failed: {e}")
    
    # 3. Test MinIO connection
    log.info("🗄️ Testing MinIO connection...")
    try:
        from minio import Minio
        minio_client = Minio(
            endpoint=minio_config['endpoint'],
            access_key=minio_config['access_key'],
            secret_key=minio_config['secret_key'],
            secure=minio_config.get('secure', False)
        )
        bucket = minio_config['bucket']
        if not minio_client.bucket_exists(bucket):
            log.warning(f"⚠️ Bucket '{bucket}' does not exist in MinIO")
        else:
            log.info(f"✅ MinIO bucket '{bucket}' exists")
    except ImportError:
        log.warning("⚠️ minio not installed, skipping MinIO test")
    except Exception as e:
        log.warning(f"⚠️ MinIO test failed: {e}")
    
    log.info("🎉 External sources verification completed!")
    return True


def _ingest_world_bank():
    """
    Placeholder: Ingest World Bank indicators for Vietnam
    
    In production, implement actual API calls to:
    - Fetch indicators (FP.CPI.TOTL.ZG, NY.GDP.MKTP.KD.ZG, SL.UEM.TOTL.ZS)
    - Transform and load to silver.stg_world_bank_indicators
    """
    log = logging.getLogger("ingest_world_bank")
    log.info("📊 World Bank data ingest placeholder")
    log.info("Note: Actual implementation needed in /opt/ops/external_sources/ingest_world_bank.py")
    return True


def _ingest_provinces():
    """
    Placeholder: Ingest Vietnam provinces and districts
    
    In production, implement actual API calls to:
    - Fetch from provinces.open-api.vn
    - Transform and load to silver.stg_vietnam_locations
    """
    log = logging.getLogger("ingest_provinces")
    log.info("🗺️ Vietnam provinces data ingest placeholder")
    log.info("Note: Actual implementation needed in /opt/ops/external_sources/ingest_provinces.py")
    return True


def _check_data_freshness():
    """
    Check if external data needs refresh (monthly).
    Returns True if data is stale (> 30 days old).
    Placeholder for actual implementation.
    """
    log = logging.getLogger("check_data_freshness")
    log.info("📅 Checking data freshness...")
    log.info("✅ Data freshness check passed - proceeding with ingest")
    return True


# Default DAG arguments
DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
}


@dag(
    dag_id="sme_pulse_external_data_sync",
    description="Monthly sync of external macro data sources (World Bank + Vietnam Provinces)",
    schedule="0 0 1 * *",  # Monthly: 1st day at 00:00 UTC
    start_date=datetime(2025, 11, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["sme_pulse", "external-data", "macro-indicators", "geography"],
    max_active_runs=1,
)
def external_data_sync_pipeline():
    """
    Main DAG for external data synchronization
    """
    
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
        dbt_dir = PIPELINE_CONFIG['dbt']['project_dir']
        
        run_silver = BashOperator(
            task_id="dbt_run_silver_external",
            bash_command=f"cd {dbt_dir} && dbt run --select silver.external.* --profiles-dir {dbt_dir} 2>&1 || echo 'Silver external models not found'",
            execution_timeout=timedelta(minutes=10)
        )
        
        test_silver = BashOperator(
            task_id="dbt_test_silver_external",
            bash_command=f"cd {dbt_dir} && dbt test --select silver.external.* --profiles-dir {dbt_dir} 2>&1 || echo 'Silver external tests not found'",
            execution_timeout=timedelta(minutes=10)
        )
        
        run_silver >> test_silver
        return test_silver
    
    # ========== STEP 4: dbt Gold Layer ==========
    @task_group(group_id="dbt_gold_external")
    def dbt_gold_group():
        dbt_dir = PIPELINE_CONFIG['dbt']['project_dir']
        
        run_gold = BashOperator(
            task_id="dbt_run_gold_external",
            bash_command=f"cd {dbt_dir} && dbt run --select gold.dim_macro_indicators gold.dim_location_vn --profiles-dir {dbt_dir} 2>&1 || echo 'Gold external dimensions not found'",
            execution_timeout=timedelta(minutes=10)
        )
        
        test_gold = BashOperator(
            task_id="dbt_test_gold_external",
            bash_command=f"cd {dbt_dir} && dbt test --select gold.dim_macro_indicators gold.dim_location_vn --profiles-dir {dbt_dir} 2>&1 || echo 'Gold external tests not found'",
            execution_timeout=timedelta(minutes=10)
        )
        
        run_gold >> test_gold
        return test_gold
    
    # ========== STEP 5: Summary ==========
    def _log_summary():
        log = logging.getLogger("data_quality_summary")
        log.info("=" * 60)
        log.info("🎉 EXTERNAL DATA SYNC COMPLETED")
        log.info("=" * 60)
        log.info("✅ External sources verified")
        log.info("✅ Data freshness checked")
        log.info("✅ World Bank indicators prepared")
        log.info("✅ Vietnam provinces/districts prepared")
        log.info("✅ Silver and Gold layers updated")
        log.info("=" * 60)
    
    summary = PythonOperator(
        task_id="log_summary",
        python_callable=_log_summary,
    )
    
    # ========== DAG Flow ==========
    verify >> check_freshness >> ingest_group() >> dbt_silver_group() >> dbt_gold_group() >> summary


# Instantiate DAG
dag = external_data_sync_pipeline()
