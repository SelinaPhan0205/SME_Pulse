#!/usr/bin/env python3
"""
Load data from PostgreSQL App DB to MinIO Bronze Layer
Purpose: Extract transactional data and save as Parquet files
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "airflow" / "dags"))

import yaml
from utils.postgres_helpers import (
    extract_ar_invoices,
    extract_payments, 
    extract_payment_allocations,
    save_to_parquet_minio
)
from datetime import datetime

# Load config
CONFIG_PATH = Path(__file__).parent.parent / "airflow" / "dags" / "config" / "pipeline_config.yml"
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

postgres_cfg = config['postgres']
minio_cfg = config['minio']

print("=" * 80)
print("LOAD DATA: PostgreSQL → Bronze (MinIO)")
print("=" * 80)

# Test MinIO connection
print("\n[Step 1] Testing MinIO connection...")
try:
    from minio import Minio
    client = Minio(
        minio_cfg['endpoint'],
        access_key=minio_cfg['access_key'],
        secret_key=minio_cfg['secret_key'],
        secure=False
    )
    client.list_buckets()
    print("✅ MinIO connection successful")
except Exception as e:
    print(f"❌ MinIO error: {e}")
    sys.exit(1)

# Extract and load AR Invoices
print("\n[Step 2] Extracting & loading AR Invoices...")
try:
    df_invoices = extract_ar_invoices(postgres_cfg)
    print(f"✅ Extracted {len(df_invoices)} invoices")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = f"bronze/raw/app_db/ar_invoices/{timestamp}.parquet"
    save_to_parquet_minio(df_invoices, minio_cfg, 'sme-pulse', path)
    print(f"✅ Saved to MinIO: s3a://sme-pulse/{path}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Extract and load Payments
print("\n[Step 3] Extracting & loading Payments...")
try:
    df_payments = extract_payments(postgres_cfg)
    print(f"✅ Extracted {len(df_payments)} payments")
    
    path = f"bronze/raw/app_db/payments/{timestamp}.parquet"
    save_to_parquet_minio(df_payments, minio_cfg, 'sme-pulse', path)
    print(f"✅ Saved to MinIO: s3a://sme-pulse/{path}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Extract and load Payment Allocations
print("\n[Step 4] Extracting & loading Payment Allocations...")
try:
    df_allocations = extract_payment_allocations(postgres_cfg)
    print(f"✅ Extracted {len(df_allocations)} allocations")
    
    path = f"bronze/raw/app_db/payment_allocations/{timestamp}.parquet"
    save_to_parquet_minio(df_allocations, minio_cfg, 'sme-pulse', path)
    print(f"✅ Saved to MinIO: s3a://sme-pulse/{path}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ DATA LOADING COMPLETED")
print("=" * 80)
print("\nNext steps:")
print("1. Create external tables in Trino")
print("2. Run dbt models (stg_ar_invoices_app_db, fact_ar_invoices_app_db)")
print("3. Verify data in Silver & Gold layers")

