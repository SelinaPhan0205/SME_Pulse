#!/usr/bin/env python3
"""
Check Parquet file schema in MinIO
"""

import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "airflow" / "dags"))

import yaml
import pandas as pd
from minio import Minio
import io

# Load config
CONFIG_PATH = Path(__file__).parent.parent / "airflow" / "dags" / "config" / "pipeline_config.yml"
with open(CONFIG_PATH, 'r') as f:
    config = yaml.safe_load(f)

minio_cfg = config['minio']

print("=" * 80)
print("CHECK PARQUET FILE SCHEMA")
print("=" * 80)

# Connect to MinIO
try:
    client = Minio(
        minio_cfg['endpoint'],
        access_key=minio_cfg['access_key'],
        secret_key=minio_cfg['secret_key'],
        secure=False
    )
    print(f"✅ Connected to MinIO: {minio_cfg['endpoint']}")
except Exception as e:
    print(f"❌ MinIO error: {e}")
    sys.exit(1)

# List objects
bucket = "sme_pulse"
prefix = "bronze/raw/app_db/"

print(f"\n📁 Listing objects in {bucket}/{prefix}...")
try:
    objects = client.list_objects(bucket, prefix=prefix, recursive=True)
    file_list = list(objects)
    
    if not file_list:
        print(f"❌ No files found in {bucket}/{prefix}")
        sys.exit(1)
    
    print(f"✅ Found {len(file_list)} files:")
    for obj in file_list:
        print(f"   - {obj.object_name} ({obj.size} bytes)")
    
    # Read first file
    first_file = file_list[0]
    print(f"\n📖 Reading first file: {first_file.object_name}")
    
    response = client.get_object(bucket, first_file.object_name)
    parquet_data = response.read()
    response.close()
    
    print(f"   ✅ Downloaded {len(parquet_data)} bytes")
    
    # Read with pandas
    df = pd.read_parquet(io.BytesIO(parquet_data))
    
    print(f"\n📊 Parquet Schema:")
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {len(df.columns)}")
    print(f"\n   Columns:")
    for col, dtype in df.dtypes.items():
        print(f"   - {col}: {dtype}")
    
    print(f"\n📋 First 3 rows:")
    print(df.head(3).to_string())
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ SCHEMA CHECK COMPLETED")
print("=" * 80)

