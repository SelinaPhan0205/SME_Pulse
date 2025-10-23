#!/usr/bin/env python3
"""
Reorganize MinIO Bronze bucket structure
From: bronze/raw/kaggle_vietnam_retail/sales_transactions/ingest_date=YYYY-MM-DD/{_source,parquet,_logs}
To:   bronze/{source/sales_snapshot, raw/sales_snapshot}
"""

import boto3
import os
from datetime import datetime
from pathlib import Path
import pyarrow.parquet as pq
import pandas as pd
from io import BytesIO

# MinIO config
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = "bronze"

# S3 client
s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name="us-east-1",
)

def list_objects(bucket, prefix):
    """List all objects in S3 with prefix"""
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        if "Contents" in response:
            return [obj["Key"] for obj in response["Contents"]]
    except Exception as e:
        print(f"Error listing objects: {e}")
    return []

def copy_object(bucket, src_key, dst_key):
    """Copy object from src to dst"""
    try:
        copy_source = {"Bucket": bucket, "Key": src_key}
        s3_client.copy_object(
            Bucket=bucket,
            CopySource=copy_source,
            Key=dst_key,
        )
        print(f"✅ Copied: {src_key} → {dst_key}")
        return True
    except Exception as e:
        print(f"❌ Error copying {src_key}: {e}")
        return False

def delete_object(bucket, key):
    """Delete object from S3"""
    try:
        s3_client.delete_object(Bucket=bucket, Key=key)
        print(f"🗑️  Deleted: {key}")
        return True
    except Exception as e:
        print(f"❌ Error deleting {key}: {e}")
        return False

def merge_parquet_files(bucket, parquet_keys, output_key):
    """Merge multiple Parquet files into one"""
    try:
        print(f"\n📦 Merging {len(parquet_keys)} Parquet files...")
        
        dfs = []
        for key in parquet_keys:
            # Download Parquet from S3
            response = s3_client.get_object(Bucket=bucket, Key=key)
            df = pd.read_parquet(BytesIO(response["Body"].read()))
            dfs.append(df)
            print(f"  ✅ Loaded: {key} ({len(df)} rows)")
        
        # Merge all DataFrames
        merged_df = pd.concat(dfs, ignore_index=True)
        print(f"\n✅ Total merged: {len(merged_df)} rows")
        
        # Save to Parquet
        parquet_buffer = BytesIO()
        merged_df.to_parquet(parquet_buffer, index=False, engine="pyarrow", compression="snappy")
        parquet_buffer.seek(0)
        
        # Upload merged Parquet
        s3_client.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=parquet_buffer.getvalue(),
        )
        print(f"✅ Uploaded merged Parquet: {output_key}")
        return True
    except Exception as e:
        print(f"❌ Error merging Parquet: {e}")
        return False

def reorganize_bronze():
    """Main reorganization function"""
    print("=" * 70)
    print("🔄 REORGANIZING BRONZE STRUCTURE")
    print("=" * 70)
    
    # OLD STRUCTURE PATHS
    old_source_prefix = "raw/kaggle_vietnam_retail/sales_transactions/ingest_date=2025-10-22/_source/"
    old_parquet_prefix = "raw/kaggle_vietnam_retail/sales_transactions/ingest_date=2025-10-22/parquet/"
    old_logs_prefix = "raw/kaggle_vietnam_retail/sales_transactions/ingest_date=2025-10-22/_logs/"
    
    # NEW STRUCTURE PATHS
    new_source_prefix = "source/sales_snapshot/"
    new_raw_prefix = "raw/sales_snapshot/"
    
    # List old structure
    print("\n📋 OLD STRUCTURE:")
    old_csv_files = list_objects(MINIO_BUCKET, old_source_prefix)
    old_parquet_files = list_objects(MINIO_BUCKET, old_parquet_prefix)
    
    print(f"  CSV files: {len(old_csv_files)}")
    print(f"  Parquet files: {len(old_parquet_files)}")
    
    # STEP 1: Copy CSV files to new source location
    print("\n" + "=" * 70)
    print("STEP 1️⃣  : Copy CSV files to source/sales_snapshot/")
    print("=" * 70)
    
    for csv_key in old_csv_files:
        # Extract filename (e.g., TT_T01_2022_split_1.csv)
        filename = csv_key.split("/")[-1]
        new_key = new_source_prefix + filename
        copy_object(MINIO_BUCKET, csv_key, new_key)
    
    # STEP 2: Merge Parquet files to raw/sales_snapshot/batch_<timestamp>.parquet
    print("\n" + "=" * 70)
    print("STEP 2️⃣  : Merge & upload Parquet to raw/sales_snapshot/")
    print("=" * 70)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_parquet_key = f"{new_raw_prefix}batch_{timestamp}.parquet"
    
    if old_parquet_files:
        merge_parquet_files(MINIO_BUCKET, old_parquet_files, output_parquet_key)
    
    # STEP 3: Delete old structure
    print("\n" + "=" * 70)
    print("STEP 3️⃣  : Delete old structure")
    print("=" * 70)
    
    all_old_keys = old_csv_files + old_parquet_files + list_objects(MINIO_BUCKET, old_logs_prefix)
    for key in all_old_keys:
        delete_object(MINIO_BUCKET, key)
    
    # STEP 4: Verify new structure
    print("\n" + "=" * 70)
    print("STEP 4️⃣  : Verify new structure")
    print("=" * 70)
    
    new_source_files = list_objects(MINIO_BUCKET, new_source_prefix)
    new_raw_files = list_objects(MINIO_BUCKET, new_raw_prefix)
    
    print(f"\n✅ NEW STRUCTURE:")
    print(f"  bronze/source/sales_snapshot/: {len(new_source_files)} files")
    for f in new_source_files:
        print(f"    - {f.split('/')[-1]}")
    
    print(f"\n  bronze/raw/sales_snapshot/: {len(new_raw_files)} files")
    for f in new_raw_files:
        print(f"    - {f.split('/')[-1]}")
    
    print("\n" + "=" * 70)
    print("✅ REORGANIZATION COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    reorganize_bronze()
