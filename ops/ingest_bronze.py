#!/usr/bin/env python3
"""
===================================================
Script: Ingest Data into Bronze Layer (Iceberg) - FAST via S3
===================================================
Mục đích:
  - Đọc CSV từ Kaggle
  - Convert → Parquet
  - Upload lên MinIO (S3)
  - COPY FROM S3 vào Iceberg (100x nhanh!)

Usage:
  python ops/ingest_bronze.py --all-files
  python ops/ingest_bronze.py --file TT_T01_2022_split_1.csv
===================================================
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
import hashlib
import pandas as pd
import trino
import boto3
from io import BytesIO

# Trino config
TRINO_HOST = "trino"
TRINO_PORT = 8080
TRINO_USER = "airflow"
TRINO_CATALOG = "iceberg"
TRINO_SCHEMA = "bronze"

# MinIO S3 config
S3_ENDPOINT = "http://minio:9000"
S3_ACCESS_KEY = "minioadmin"
S3_SECRET_KEY = "minioadmin"
S3_BUCKET = "lakehouse"
S3_REGION = "us-east-1"


def get_trino_connection():
    """Tạo connection tới Trino"""
    conn = trino.dbapi.connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user=TRINO_USER,
        catalog=TRINO_CATALOG,
        schema=TRINO_SCHEMA,
        http_scheme="http"
    )
    return conn


def get_s3_client():
    """Tạo S3 client cho MinIO"""
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION
    )


def transform_csv_to_parquet(csv_file_path: Path) -> pd.DataFrame:
    """
    Đọc CSV và transform sang Bronze schema
    
    Args:
        csv_file_path: Path to CSV file
    
    Returns:
        DataFrame in Bronze format
    """
    print(f"📖 Reading CSV: {csv_file_path.name}")
    
    # Đọc CSV
    df = pd.read_csv(csv_file_path, encoding='utf-8')
    print(f"✅ Read {len(df):,} rows × {len(df.columns)} columns")
    
    # Transform sang Bronze schema
    now = datetime.now()
    
    bronze_data = {
        'id': range(1, len(df) + 1),
        'event_id': [f"kaggle_{csv_file_path.stem}_{i}_{hashlib.md5(json.dumps(dict(row), sort_keys=True, default=str).encode()).hexdigest()[:8]}" 
                     for i, (_, row) in enumerate(df.iterrows())],
        'source': 'KAGGLE_VIETNAM_RETAIL',
        'domain': 'sales',
        'org_id': df.get('Store_ID', 'UNKNOWN').astype(str) if 'Store_ID' in df.columns else 'UNKNOWN',
        'updated_at': now,
        'ingested_at': now,
        'hash': df.apply(lambda row: hashlib.md5(json.dumps(dict(row), sort_keys=True, default=str).encode()).hexdigest(), axis=1),
        'payload_json': df.apply(lambda row: json.dumps(dict(row), default=str), axis=1)
    }
    
    bronze_df = pd.DataFrame(bronze_data)
    print(f"✅ Transformed to Bronze schema: {len(bronze_df):,} rows")
    
    return bronze_df


def upload_parquet_to_s3(df: pd.DataFrame, parquet_filename: str) -> str:
    """
    Upload Parquet file to MinIO S3
    
    Args:
        df: DataFrame to save
        parquet_filename: Name of file (e.g., TT_T01_2022.parquet)
    
    Returns:
        S3 path (s3a://bucket/path)
    """
    s3_path = f"bronze/staging/{parquet_filename}"
    
    print(f"📤 Uploading to S3: {s3_path}")
    
    # Convert to Parquet in memory
    parquet_buffer = BytesIO()
    df.to_parquet(parquet_buffer, index=False, compression='snappy')
    parquet_size_mb = parquet_buffer.tell() / 1024 / 1024
    parquet_buffer.seek(0)
    
    # Upload to MinIO
    try:
        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_path,
            Body=parquet_buffer.getvalue()
        )
        print(f"✅ Uploaded {len(df):,} rows ({parquet_size_mb:.2f} MB)")
    except Exception as e:
        print(f"❌ Error uploading to S3: {e}")
        raise
    
    return f"s3a://{S3_BUCKET}/{s3_path}"


def ingest_from_s3(s3_paths: list):
    """
    INSERT FROM Parquet files on S3 into Iceberg (FAST!)
    
    Args:
        s3_paths: List of s3a:// paths
    """
    conn = get_trino_connection()
    cursor = conn.cursor()
    
    try:
        print(f"\n💾 Ingesting {len(s3_paths)} Parquet files from S3...")
        start_time = datetime.now()
        total_rows = 0
        
        for i, s3_path in enumerate(s3_paths, 1):
            print(f"  [{i}/{len(s3_paths)}] Loading: {Path(s3_path).name}")
            
            # INSERT FROM Parquet (Trino reads directly from S3)
            sql = f"""
            INSERT INTO iceberg.bronze.transactions_raw
            SELECT * FROM read_parquet('{s3_path}')
            """
            
            cursor.execute(sql)
            
            # Get row count for this file
            print(f"     ✅ Loaded")
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n✅ All files loaded in {elapsed:.1f}s")
        
        # Verify total counts
        cursor.execute("SELECT COUNT(*) as total FROM iceberg.bronze.transactions_raw")
        result = cursor.fetchone()
        total_rows = result[0] if result else 0
        
        cursor.execute("SELECT COUNT(*), source FROM iceberg.bronze.transactions_raw GROUP BY source")
        results = cursor.fetchall()
        
        print(f"\n📊 Total rows: {total_rows:,}")
        print(f"📊 Counts by source:")
        for row in results:
            print(f"   {row[1]}: {row[0]:,}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def find_sales_csv_files(data_dir: Path) -> list:
    """Find all CSV files in Sales_snapshot_data"""
    sales_dir = data_dir / "InventoryAndSale_snapshot_data" / "Sales_snapshot_data"
    
    if not sales_dir.exists():
        print(f"❌ Sales directory not found: {sales_dir}")
        return []
    
    csv_files = sorted(sales_dir.glob("*.csv"))
    print(f"📂 Found {len(csv_files)} CSV files")
    
    return csv_files


def main():
    parser = argparse.ArgumentParser(description="Fast ingest Kaggle data via S3 + Parquet")
    parser.add_argument("--file", help="Specific CSV file")
    parser.add_argument("--all-files", action="store_true", help="All CSV files")
    parser.add_argument("--data-dir", default="data", help="Data directory")
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / args.data_dir
    
    print(f"🚀 Fast Ingest - CSV → Parquet → S3 → Iceberg")
    print(f"📁 Data directory: {data_dir.absolute()}\n")
    
    # Find CSV files
    csv_files = []
    if args.file:
        csv_path = data_dir / "InventoryAndSale_snapshot_data" / "Sales_snapshot_data" / args.file
        csv_files = [csv_path] if csv_path.exists() else []
    elif args.all_files:
        csv_files = find_sales_csv_files(data_dir)
    else:
        print("❌ Use --file <name> or --all-files")
        return
    
    if not csv_files:
        print("❌ No CSV files found")
        return
    
    # Process each CSV
    s3_paths = []
    total_rows = 0
    
    for csv_file in csv_files:
        print(f"\n{'='*70}")
        print(f"Processing: {csv_file.name}")
        print(f"{'='*70}")
        
        try:
            # Transform CSV → Parquet
            df = transform_csv_to_parquet(csv_file)
            total_rows += len(df)
            
            # Upload to S3
            parquet_name = csv_file.stem.replace(' ', '_') + '.parquet'
            s3_path = upload_parquet_to_s3(df, parquet_name)
            s3_paths.append(s3_path)
        except Exception as e:
            print(f"❌ Error processing {csv_file.name}: {e}")
            continue
    
    print(f"\n{'='*70}")
    print(f"📦 Total rows: {total_rows:,}")
    print(f"📦 Parquet files ready: {len(s3_paths)}")
    print(f"{'='*70}")
    
    # Ingest from S3
    if s3_paths:
        ingest_from_s3(s3_paths)
        print("\n✅ Ingest completed!")
    else:
        print("⚠️  No files to ingest")


if __name__ == "__main__":
    main()#!/usr/bin/env python3
"""
===================================================
Script: Ingest Data into Bronze Layer (Iceberg) - FAST via S3
===================================================
Mục đích:
  - Đọc CSV từ Kaggle
  - Convert → Parquet
  - Upload lên MinIO (S3)
  - COPY FROM S3 vào Iceberg (100x nhanh!)

Usage:
  python ops/ingest_bronze.py --all-files
  python ops/ingest_bronze.py --file TT_T01_2022_split_1.csv
===================================================
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
import hashlib
import pandas as pd
import trino
import boto3
from io import BytesIO

# Trino config
TRINO_HOST = "trino"
TRINO_PORT = 8080
TRINO_USER = "airflow"
TRINO_CATALOG = "iceberg"
TRINO_SCHEMA = "bronze"

# MinIO S3 config
S3_ENDPOINT = "http://minio:9000"
S3_ACCESS_KEY = "minioadmin"
S3_SECRET_KEY = "minioadmin"
S3_BUCKET = "lakehouse"
S3_REGION = "us-east-1"


def get_trino_connection():
    """Tạo connection tới Trino"""
    conn = trino.dbapi.connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user=TRINO_USER,
        catalog=TRINO_CATALOG,
        schema=TRINO_SCHEMA,
        http_scheme="http"
    )
    return conn


def get_s3_client():
    """Tạo S3 client cho MinIO"""
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION
    )


def transform_csv_to_parquet(csv_file_path: Path) -> pd.DataFrame:
    """
    Đọc CSV và transform sang Bronze schema
    
    Args:
        csv_file_path: Path to CSV file
    
    Returns:
        DataFrame in Bronze format
    """
    print(f"📖 Reading CSV: {csv_file_path.name}")
    
    # Đọc CSV
    df = pd.read_csv(csv_file_path, encoding='utf-8')
    print(f"✅ Read {len(df):,} rows × {len(df.columns)} columns")
    
    # Transform sang Bronze schema
    now = datetime.now()
    
    bronze_data = {
        'id': range(1, len(df) + 1),
        'event_id': [f"kaggle_{csv_file_path.stem}_{i}_{hashlib.md5(json.dumps(dict(row), sort_keys=True, default=str).encode()).hexdigest()[:8]}" 
                     for i, (_, row) in enumerate(df.iterrows())],
        'source': 'KAGGLE_VIETNAM_RETAIL',
        'domain': 'sales',
        'org_id': df.get('Store_ID', 'UNKNOWN').astype(str) if 'Store_ID' in df.columns else 'UNKNOWN',
        'updated_at': now,
        'ingested_at': now,
        'hash': df.apply(lambda row: hashlib.md5(json.dumps(dict(row), sort_keys=True, default=str).encode()).hexdigest(), axis=1),
        'payload_json': df.apply(lambda row: json.dumps(dict(row), default=str), axis=1)
    }
    
    bronze_df = pd.DataFrame(bronze_data)
    print(f"✅ Transformed to Bronze schema: {len(bronze_df):,} rows")
    
    return bronze_df


def upload_parquet_to_s3(df: pd.DataFrame, parquet_filename: str) -> str:
    """
    Upload Parquet file to MinIO S3
    
    Args:
        df: DataFrame to save
        parquet_filename: Name of file (e.g., TT_T01_2022.parquet)
    
    Returns:
        S3 path (s3a://bucket/path)
    """
    s3_path = f"bronze/staging/{parquet_filename}"
    
    print(f"📤 Uploading to S3: {s3_path}")
    
    # Convert to Parquet in memory
    parquet_buffer = BytesIO()
    df.to_parquet(parquet_buffer, index=False, compression='snappy')
    parquet_size_mb = parquet_buffer.tell() / 1024 / 1024
    parquet_buffer.seek(0)
    
    # Upload to MinIO
    try:
        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_path,
            Body=parquet_buffer.getvalue()
        )
        print(f"✅ Uploaded {len(df):,} rows ({parquet_size_mb:.2f} MB)")
    except Exception as e:
        print(f"❌ Error uploading to S3: {e}")
        raise
    
    return f"s3a://{S3_BUCKET}/{s3_path}"


def ingest_from_s3(s3_paths: list):
    """
    INSERT FROM Parquet files on S3 into Iceberg (FAST!)
    
    Args:
        s3_paths: List of s3a:// paths
    """
    conn = get_trino_connection()
    cursor = conn.cursor()
    
    try:
        print(f"\n💾 Ingesting {len(s3_paths)} Parquet files from S3...")
        start_time = datetime.now()
        total_rows = 0
        
        for i, s3_path in enumerate(s3_paths, 1):
            print(f"  [{i}/{len(s3_paths)}] Loading: {Path(s3_path).name}")
            
            # INSERT FROM Parquet (Trino reads directly from S3)
            sql = f"""
            INSERT INTO iceberg.bronze.transactions_raw
            SELECT * FROM read_parquet('{s3_path}')
            """
            
            cursor.execute(sql)
            
            # Get row count for this file
            print(f"     ✅ Loaded")
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n✅ All files loaded in {elapsed:.1f}s")
        
        # Verify total counts
        cursor.execute("SELECT COUNT(*) as total FROM iceberg.bronze.transactions_raw")
        result = cursor.fetchone()
        total_rows = result[0] if result else 0
        
        cursor.execute("SELECT COUNT(*), source FROM iceberg.bronze.transactions_raw GROUP BY source")
        results = cursor.fetchall()
        
        print(f"\n📊 Total rows: {total_rows:,}")
        print(f"📊 Counts by source:")
        for row in results:
            print(f"   {row[1]}: {row[0]:,}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def find_sales_csv_files(data_dir: Path) -> list:
    """Find all CSV files in Sales_snapshot_data"""
    sales_dir = data_dir / "InventoryAndSale_snapshot_data" / "Sales_snapshot_data"
    
    if not sales_dir.exists():
        print(f"❌ Sales directory not found: {sales_dir}")
        return []
    
    csv_files = sorted(sales_dir.glob("*.csv"))
    print(f"📂 Found {len(csv_files)} CSV files")
    
    return csv_files


def main():
    parser = argparse.ArgumentParser(description="Fast ingest Kaggle data via S3 + Parquet")
    parser.add_argument("--file", help="Specific CSV file")
    parser.add_argument("--all-files", action="store_true", help="All CSV files")
    parser.add_argument("--data-dir", default="data", help="Data directory")
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / args.data_dir
    
    print(f"🚀 Fast Ingest - CSV → Parquet → S3 → Iceberg")
    print(f"📁 Data directory: {data_dir.absolute()}\n")
    
    # Find CSV files
    csv_files = []
    if args.file:
        csv_path = data_dir / "InventoryAndSale_snapshot_data" / "Sales_snapshot_data" / args.file
        csv_files = [csv_path] if csv_path.exists() else []
    elif args.all_files:
        csv_files = find_sales_csv_files(data_dir)
    else:
        print("❌ Use --file <name> or --all-files")
        return
    
    if not csv_files:
        print("❌ No CSV files found")
        return
    
    # Process each CSV
    s3_paths = []
    total_rows = 0
    
    for csv_file in csv_files:
        print(f"\n{'='*70}")
        print(f"Processing: {csv_file.name}")
        print(f"{'='*70}")
        
        try:
            # Transform CSV → Parquet
            df = transform_csv_to_parquet(csv_file)
            total_rows += len(df)
            
            # Upload to S3
            parquet_name = csv_file.stem.replace(' ', '_') + '.parquet'
            s3_path = upload_parquet_to_s3(df, parquet_name)
            s3_paths.append(s3_path)
        except Exception as e:
            print(f"❌ Error processing {csv_file.name}: {e}")
            continue
    
    print(f"\n{'='*70}")
    print(f"📦 Total rows: {total_rows:,}")
    print(f"📦 Parquet files ready: {len(s3_paths)}")
    print(f"{'='*70}")
    
    # Ingest from S3
    if s3_paths:
        ingest_from_s3(s3_paths)
        print("\n✅ Ingest completed!")
    else:
        print("⚠️  No files to ingest")


if __name__ == "__main__":
    main()