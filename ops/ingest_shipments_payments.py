#!/usr/bin/env python3
"""
Script: Ingest Shipments & Payments từ CSV lên MinIO (Bronze Layer)
File nguồn: data/raw/shipments_payments.csv
Đích: sme-lake/bronze/raw/shipments_payments_raw/

Mapping cột:
  - Transaction_ID: Transaction ID
  - Customer_ID: Customer ID
  - Email: Email (chuẩn hoá lowercase)
  - Phone: Phone
  - Date: Transaction date
  - Amount: Transaction amount
  - Shipping_Method: Shipping method (GHN, GHTK, VTP, etc.)
  - Payment_Method: Payment method (card, cash, transfer, etc.)
  - Order_Status: Status (pending, shipped, delivered, etc.)
  - Product_Category, Product_Brand: Product info
  - Year, Month: Year/Month partition

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

# MinIO connection
MINIO_HOST = os.getenv("MINIO_HOST", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = "sme-lake"
MINIO_BRONZE_PREFIX = "bronze/raw/shipments_payments_raw"

# Local paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
CSV_FILE = DATA_RAW_DIR / "shipments_payments.csv"
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


def normalize_shipments_payments(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hoá & validate dữ liệu Shipments & Payments
    - Convert kiểu dữ liệu
    - Chuẩn hoá email/phone
    - Handle missing values
    - Add metadata
    - Map danh mục (channel, payment method, carrier)
    """
    logger.info(f"  Normalizing {len(df)} rows...")
    
    # Convert date
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="coerce")
    
    # Convert numeric
    numeric_cols = ["Age", "Income", "Total_Purchases", "Amount", "Total_Amount", "Ratings"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Normalize email (lowercase, strip whitespace)
    df["Email"] = df["Email"].fillna("").str.lower().str.strip()
    
    # Normalize phone (remove special chars, keep only digits)
    df["Phone"] = df["Phone"].fillna("").astype(str).str.replace(r"\D", "", regex=True)
    
    # Chuẩn hoá Shipping Method (map sang danh mục VN: GHN, GHTK, VTP, etc.)
    shipping_map = {
        "same-day": "GHN",
        "express": "GHTK",
        "standard": "VTP",
        "ghn": "GHN",
        "ghtk": "GHTK",
        "vtp": "VTP"
    }
    df["Shipping_Method"] = df["Shipping_Method"].fillna("OTHER").str.lower()
    df["Shipping_Method"] = df["Shipping_Method"].map(
        lambda x: shipping_map.get(x, "OTHER")
    )
    
    # Chuẩn hoá Payment Method
    payment_map = {
        "credit card": "card",
        "debit card": "card",
        "credit": "card",
        "debit": "card",
        "cash": "cash",
        "paypal": "transfer",
        "vietqr": "vietqr",
        "momo": "momo",
        "zalopay": "zalopay",
        "bank transfer": "transfer",
        "transfer": "transfer"
    }
    df["Payment_Method"] = df["Payment_Method"].fillna("OTHER").str.lower()
    df["Payment_Method"] = df["Payment_Method"].map(
        lambda x: payment_map.get(x, "other")
    )
    
    # Chuẩn hoá Order Status
    status_map = {
        "pending": "pending",
        "processing": "processing",
        "shipped": "shipped",
        "in transit": "in_transit",
        "delivered": "delivered",
        "completed": "delivered"
    }
    df["Order_Status"] = df["Order_Status"].fillna("OTHER").str.lower()
    df["Order_Status"] = df["Order_Status"].map(
        lambda x: status_map.get(x, "other")
    )
    
    # Fill missing text fields
    df["Product_Category"] = df["Product_Category"].fillna("OTHER")
    df["Product_Brand"] = df["Product_Brand"].fillna("OTHER")
    df["Product_Type"] = df["Product_Type"].fillna("OTHER")
    df["Feedback"] = df["Feedback"].fillna("")
    df["Gender"] = df["Gender"].fillna("Unknown")
    df["Customer_Segment"] = df["Customer_Segment"].fillna("Other")
    
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
        object_name = f"{MINIO_BRONZE_PREFIX}/shipments_payments.parquet"
        
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
    logger.info("🚀 INGEST: Shipments & Payments CSV → MinIO Bronze")
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
    
    # Process chunks
    chunk_idx = 0
    total_rows = 0
    all_chunks = []
    
    try:
        # Process all chunks
        for chunk in read_csv_in_chunks(CSV_FILE, chunksize=50000):
            chunk_idx += 1
            total_rows += len(chunk)
            
            # Normalize
            chunk = normalize_shipments_payments(chunk)
            all_chunks.append(chunk)
            
            logger.info(f"  Processed chunk {chunk_idx}: {len(chunk):,} rows (Total: {total_rows:,})")
        
        # Combine all chunks
        logger.info(f"\n🔗 Combining {len(all_chunks)} chunks...")
        df_combined = pd.concat(all_chunks, ignore_index=True)
        logger.info(f"  Combined DataFrame: {len(df_combined):,} rows")
        
        # Upload single file
        logger.info(f"\n☁️ Uploading to MinIO...")
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        parquet_file = WORK_DIR / "shipments_payments.parquet"
        
        upload_parquet_to_minio(client, df_combined, parquet_file)
        
        # Clean up
        parquet_file.unlink()
    
    except Exception as e:
        logger.error(f"❌ Ingest failed: {e}")
        sys.exit(1)
    
    # Summary
    logger.info("=" * 70)
    logger.info(f"✅ INGEST COMPLETED")
    logger.info(f"  Total rows: {total_rows:,}")
    logger.info(f"  Single parquet file uploaded")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
