#!/usr/bin/env python3
"""
Script: Ingest Bank Transactions từ CSV lên MinIO (Bronze Layer)
File nguồn: data/raw/Bank-Transactions.csv
Đích: sme-lake/bronze/raw/bank_txn_raw/

Mapping cột: 
  - booking_id: transaction ID
  - bookg_dt_tm_gmt: transaction date/time
  - bookg_amt_nmrc: amount (numeric)
  - acct_ccy: currency
  - ctpty_nm: counterparty name
  - end_to_end_id: end to end reference
  - bookg_cdt_dbt_ind: CRDT (in) / DBIT (out)

Ingest cách: Đọc CSV → Parquet → Upload MinIO (incremental by year_month)
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from minio import Minio
from minio.error import S3Error

# ============================================================================
# CONFIG
# ============================================================================

# MinIO connection (từ docker-compose)
MINIO_HOST = os.getenv("MINIO_HOST", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = "sme-lake"
MINIO_BRONZE_PREFIX = "bronze/raw/bank_txn_raw"

# Local paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
CSV_FILE = DATA_RAW_DIR / "Bank-Transactions.csv"
WORK_DIR = Path("/tmp") / "sme_ingest"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def connect_minio():
    """Kết nối tới MinIO"""
    try:
        client = Minio(
            MINIO_HOST,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )
        # Check connection
        client.list_buckets()
        logger.info(f"✅ Connected to MinIO: {MINIO_HOST}")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to connect MinIO: {e}")
        raise


def ensure_bucket_exists(client: Minio, bucket_name: str):
    """Tạo bucket nếu chưa tồn tại"""
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            logger.info(f"✅ Created bucket: {bucket_name}")
        else:
            logger.info(f"✅ Bucket exists: {bucket_name}")
    except S3Error as e:
        logger.error(f"❌ Error creating bucket: {e}")
        raise


def read_csv_in_chunks(csv_file: Path, chunksize: int = 50000):
    """Đọc CSV theo chunks (để tránh load hết vào memory)"""
    logger.info(f"📖 Reading CSV: {csv_file}")
    
    try:
        for i, chunk in enumerate(pd.read_csv(csv_file, chunksize=chunksize)):
            logger.info(f"  Chunk {i+1}: {len(chunk)} rows")
            yield chunk
    except Exception as e:
        logger.error(f"❌ Error reading CSV: {e}")
        raise


def normalize_bank_txn(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hoá & validate dữ liệu Bank Transactions
    - Convert kiểu dữ liệu
    - Handle missing values
    - Add metadata
    """
    logger.info(f"  Normalizing {len(df)} rows...")
    
    # Convert date
    df["bookg_dt_tm_gmt"] = pd.to_datetime(
        df["bookg_dt_tm_gmt"], 
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce"
    )
    
    # Convert numeric
    numeric_cols = ["bookg_amt_nmrc", "bal_aftr_bookg_nmrc", "bookg_amt"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Fill missing values
    df["ctpty_nm"] = df["ctpty_nm"].fillna("UNKNOWN")
    df["end_to_end_id"] = df["end_to_end_id"].fillna("")
    df["rmt_inf_ustrd1"] = df["rmt_inf_ustrd1"].fillna("")
    
    # Add ingestion metadata
    df["ingested_at"] = datetime.utcnow()
    df["ingested_year_month"] = datetime.utcnow().strftime("%Y%m")
    
    return df


def upload_parquet_to_minio(
    client: Minio,
    df: pd.DataFrame,
    parquet_file_path: Path
):
    """
    Convert DataFrame → Parquet → Upload MinIO
    Single file, no partitioning
    """
    try:
        # Convert to Parquet
        table = pa.Table.from_pandas(df)
        pq.write_table(table, str(parquet_file_path))
        
        # MinIO object name (single file)
        object_name = f"{MINIO_BRONZE_PREFIX}/bank_transactions.parquet"
        
        # Upload
        client.fput_object(
            MINIO_BUCKET,
            object_name,
            str(parquet_file_path),
            content_type="application/x-parquet"
        )
        
        logger.info(f"  ✅ Uploaded: {object_name}")
        
        return object_name
        
    except Exception as e:
        logger.error(f"❌ Error uploading Parquet: {e}")
        raise


def main():
    """Main ingest workflow"""
    
    logger.info("=" * 70)
    logger.info("🚀 INGEST: Bank Transactions CSV → MinIO Bronze")
    logger.info("=" * 70)
    
    # Check CSV exists
    if not CSV_FILE.exists():
        logger.error(f"❌ CSV file not found: {CSV_FILE}")
        sys.exit(1)
    
    logger.info(f"📍 Source: {CSV_FILE}")
    logger.info(f"📍 Destination: s3://{MINIO_BUCKET}/{MINIO_BRONZE_PREFIX}/")
    
    # Connect MinIO
    client = connect_minio()
    ensure_bucket_exists(client, MINIO_BUCKET)
    
    # Read ALL data at once (combine chunks)
    logger.info("📖 Reading CSV (all chunks)...")
    all_chunks = []
    total_rows = 0
    
    try:
        for chunk in read_csv_in_chunks(CSV_FILE, chunksize=50000):
            chunk = normalize_bank_txn(chunk)
            all_chunks.append(chunk)
            total_rows += len(chunk)
        
        # Combine all chunks
        logger.info(f"  Combining {len(all_chunks)} chunks...")
        df_combined = pd.concat(all_chunks, ignore_index=True)
        
        # Work directory
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        parquet_file = WORK_DIR / "bank_transactions_combined.parquet"
        
        # Upload single file
        obj_name = upload_parquet_to_minio(client, df_combined, parquet_file)
        
        # Clean up
        parquet_file.unlink()
    
    except Exception as e:
        logger.error(f"❌ Ingest failed: {e}")
        sys.exit(1)
    
    # Summary
    logger.info("=" * 70)
    logger.info(f"✅ INGEST COMPLETED")
    logger.info(f"  Total rows: {total_rows:,}")
    logger.info(f"  File: {obj_name}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
