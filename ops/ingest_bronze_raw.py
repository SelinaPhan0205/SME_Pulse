#!/usr/bin/env python3
"""
🗂️ Bronze Layer Ingestion - Raw Files Only
============================================
Purpose: Ingest raw Excel files to MinIO Bronze layer
Output Structure:
    s3://bronze/raw/<source>/<entity>/ingest_date=YYYY-MM-DD/
        ├─ _source/       # Original Excel files (.xlsx, .xls)
        ├─ parquet/       # Converted Parquet files (for Silver to read)
        └─ _logs/         # Manifest JSON (metadata)

Rules:
- ❌ NO Iceberg tables in Bronze
- ❌ NO schema transformations
- ✅ ONLY immutable raw files
- ✅ Original Excel + Parquet conversion
- ✅ Manifest logging for audit
"""

import argparse
import json
import hashlib
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any
import boto3
from botocore.client import Config

# ==================== CONFIG ====================
MINIO_ENDPOINT = "http://minio:9000"
MINIO_ACCESS_KEY = "minio"
MINIO_SECRET_KEY = "minio123"
BRONZE_BUCKET = "bronze"
DATA_DIR = Path("/opt/data/InventoryAndSale_snapshot_data/Sales_snapshot_data")

# ==================== S3 CLIENT ====================
s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def ingest_all_files(source: str, entity: str):
    """Ingest all CSV files and merge into single Parquet file"""
    
    ingest_date = datetime.now().strftime("%Y-%m-%d")
    csv_files = list(DATA_DIR.glob("*.csv"))
    
    if not csv_files:
        print(f"❌ No CSV files found in {DATA_DIR}")
        return
    
    print(f"\n🚀 Bronze Raw Ingestion")
    print(f"📁 Source directory: {DATA_DIR}")
    print(f"📊 Found {len(csv_files)} CSV files")
    print(f"📅 Ingest date: {ingest_date}")
    
    # Step 1: Read and merge all CSV files
    print(f"\n{'='*70}")
    print(f"📥 Reading and merging {len(csv_files)} CSV files...")
    print(f"{'='*70}")
    
    all_dataframes = []
    total_csv_size = 0
    
    for csv_file in csv_files:
        print(f"   Reading: {csv_file.name} ({csv_file.stat().st_size:,} bytes)")
        df = pd.read_csv(csv_file)
        all_dataframes.append(df)
        total_csv_size += csv_file.stat().st_size
    
    # Merge all dataframes
    merged_df = pd.concat(all_dataframes, ignore_index=True)
    total_rows = len(merged_df)
    
    print(f"\n✅ Merged {len(csv_files)} files → {total_rows:,} total rows")
    
    # Step 2: Upload single merged Parquet file
    batch_filename = f"batch_{ingest_date.replace('-', '')}_211608.parquet"
    parquet_s3_key = f"raw/sales_snapshot/{batch_filename}"
    
    print(f"\n{'='*70}")
    print(f"📤 Uploading single Parquet file: {batch_filename}")
    print(f"{'='*70}")
    
    # Convert to Parquet buffer
    parquet_buffer = merged_df.to_parquet(
        engine='pyarrow',
        compression='snappy',
        index=False
    )
    
    # Upload to MinIO
    s3_client.put_object(
        Bucket=BRONZE_BUCKET,
        Key=parquet_s3_key,
        Body=parquet_buffer,
        Metadata={
            'source_files': str(len(csv_files)),
            'row_count': str(total_rows),
            'compression': 'snappy',
            'ingest_date': ingest_date
        }
    )
    
    parquet_size = len(parquet_buffer)
    
    print(f"✅ Uploaded: s3://{BRONZE_BUCKET}/{parquet_s3_key}")
    print(f"   Rows: {total_rows:,}")
    print(f"   Size: {parquet_size:,} bytes ({parquet_size/1024/1024:.2f} MB)")
    print(f"   Compression ratio: {total_csv_size/parquet_size:.2f}x")
    
    # Step 3: Upload individual CSVs to source/ (for audit)
    print(f"\n{'='*70}")
    print(f"📄 Uploading original CSV files to source/...")
    print(f"{'='*70}")
    
    for csv_file in csv_files:
        source_s3_key = f"source/sales_snapshot/{csv_file.name}"
        with open(csv_file, 'rb') as f:
            s3_client.put_object(
                Bucket=BRONZE_BUCKET,
                Key=source_s3_key,
                Body=f,
                Metadata={'ingest_date': ingest_date}
            )
        print(f"   ✅ {csv_file.name}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 Ingestion Summary")
    print(f"{'='*70}")
    print(f"✅ CSV files uploaded: {len(csv_files)}")
    print(f"📈 Total rows: {total_rows:,}")
    print(f"💾 CSV total size: {total_csv_size:,} bytes ({total_csv_size/1024/1024:.2f} MB)")
    print(f"💾 Parquet size: {parquet_size:,} bytes ({parquet_size/1024/1024:.2f} MB)")
    print(f"🗂️  CSV files: s3://{BRONZE_BUCKET}/source/sales_snapshot/")
    print(f"🗂️  Parquet (SINGLE FILE): s3://{BRONZE_BUCKET}/{parquet_s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Ingest raw CSV files to Bronze layer")
    parser.add_argument("--source", default="kaggle_vietnam_retail", help="Data source name")
    parser.add_argument("--entity", default="sales_transactions", help="Entity/table name")
    
    args = parser.parse_args()
    
    ingest_all_files(source=args.source, entity=args.entity)


if __name__ == "__main__":
    main()
