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


def upload_to_bronze(
    local_file: Path,
    source: str,
    entity: str,
    ingest_date: str
) -> Dict[str, Any]:
    """
    Upload raw file to Bronze layer
    
    Steps:
    1. Upload original file to _source/
    2. Convert Excel to Parquet
    3. Upload Parquet to parquet/
    4. Generate and upload manifest to _logs/
    
    Returns:
        manifest: Dict with metadata
    """
    
    file_name = local_file.name
    file_size = local_file.stat().st_size
    file_hash = calculate_file_hash(local_file)
    
    # S3 paths
    base_path = f"raw/{source}/{entity}/ingest_date={ingest_date}"
    source_s3_key = f"{base_path}/_source/{file_name}"
    
    print(f"\n{'='*70}")
    print(f"📤 Uploading: {file_name}")
    print(f"{'='*70}")
    
    # Step 1: Upload original file
    print(f"1️⃣  Uploading original file to s3://{BRONZE_BUCKET}/{source_s3_key}")
    with open(local_file, 'rb') as f:
        s3_client.put_object(
            Bucket=BRONZE_BUCKET,
            Key=source_s3_key,
            Body=f,
            Metadata={
                'source': source,
                'entity': entity,
                'ingest_date': ingest_date,
                'file_hash': file_hash,
                'original_size': str(file_size)
            }
        )
    print(f"   ✅ Uploaded original file ({file_size:,} bytes)")
    
    # Step 2: Convert CSV to Parquet
    print(f"2️⃣  Converting CSV → Parquet...")
    try:
        # Read CSV
        df = pd.read_csv(local_file)
        row_count = len(df)
        
        # Write to Parquet (in-memory buffer)
        parquet_buffer = df.to_parquet(
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        # Upload Parquet
        parquet_s3_key = f"{base_path}/parquet/{file_name.replace('.csv', '.parquet')}"
        s3_client.put_object(
            Bucket=BRONZE_BUCKET,
            Key=parquet_s3_key,
            Body=parquet_buffer,
            Metadata={
                'source_file': file_name,
                'row_count': str(row_count),
                'compression': 'snappy'
            }
        )
        print(f"   ✅ Converted to Parquet: {row_count:,} rows")
        print(f"   📁 s3://{BRONZE_BUCKET}/{parquet_s3_key}")
        
    except Exception as e:
        print(f"   ❌ Error converting to Parquet: {e}")
        row_count = None
        parquet_s3_key = None
    
    # Step 3: Generate manifest
    manifest = {
        "file_name": file_name,
        "source": source,
        "entity": entity,
        "ingest_date": ingest_date,
        "ingest_timestamp": datetime.now(timezone.utc).isoformat(),
        "file_size_bytes": file_size,
        "file_hash_sha256": file_hash,
        "row_count": row_count,
        "s3_paths": {
            "original": f"s3://{BRONZE_BUCKET}/{source_s3_key}",
            "parquet": f"s3://{BRONZE_BUCKET}/{parquet_s3_key}" if parquet_s3_key else None
        },
        "status": "success"
    }
    
    # Upload manifest
    manifest_s3_key = f"{base_path}/_logs/manifest_{file_name}.json"
    s3_client.put_object(
        Bucket=BRONZE_BUCKET,
        Key=manifest_s3_key,
        Body=json.dumps(manifest, indent=2),
        ContentType='application/json'
    )
    print(f"3️⃣  ✅ Manifest written to s3://{BRONZE_BUCKET}/{manifest_s3_key}")
    
    return manifest


def ingest_all_files(source: str, entity: str):
    """Ingest all CSV files from DATA_DIR"""
    
    ingest_date = datetime.now().strftime("%Y-%m-%d")
    excel_files = list(DATA_DIR.glob("*.csv"))
    
    if not excel_files:
        print(f"❌ No CSV files found in {DATA_DIR}")
        return
    
    print(f"\n🚀 Bronze Raw Ingestion")
    print(f"📁 Source directory: {DATA_DIR}")
    print(f"📊 Found {len(excel_files)} CSV files")
    print(f"📅 Ingest date: {ingest_date}")
    
    manifests = []
    for excel_file in excel_files:
        try:
            manifest = upload_to_bronze(
                local_file=excel_file,
                source=source,
                entity=entity,
                ingest_date=ingest_date
            )
            manifests.append(manifest)
        except Exception as e:
            print(f"❌ Error processing {excel_file.name}: {e}")
    
    # Summary
    total_rows = sum(m['row_count'] for m in manifests if m['row_count'])
    total_size = sum(m['file_size_bytes'] for m in manifests)
    
    print(f"\n{'='*70}")
    print(f"📊 Ingestion Summary")
    print(f"{'='*70}")
    print(f"✅ Files processed: {len(manifests)}/{len(excel_files)}")
    print(f"📈 Total rows: {total_rows:,}")
    print(f"💾 Total size: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
    print(f"🗂️  Bronze bucket: s3://{BRONZE_BUCKET}/raw/{source}/{entity}/ingest_date={ingest_date}/")


def main():
    parser = argparse.ArgumentParser(description="Ingest raw CSV files to Bronze layer")
    parser.add_argument("--source", default="kaggle_vietnam_retail", help="Data source name")
    parser.add_argument("--entity", default="sales_transactions", help="Entity/table name")
    
    args = parser.parse_args()
    
    ingest_all_files(source=args.source, entity=args.entity)


if __name__ == "__main__":
    main()
