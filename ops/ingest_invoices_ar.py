"""
Ingest AR Invoices CSV to Bronze Layer (MinIO)

Input: data/raw/invoices_AR.csv
Output: bronze/raw/invoices_AR/invoices_AR.parquet (MinIO)
Also upload original CSV to bronze/source/invoices_AR/

Usage:
    python ops/ingest_invoices_ar.py --input data/raw/invoices_AR.csv --bucket sme-lake \
        --bronze-raw bronze/raw/invoices_AR/ --bronze-source bronze/source/invoices_AR/

If run inside Airflow/DBT Docker: paths are /opt/data/raw/invoices_AR.csv etc.
"""
import os
import argparse
import pandas as pd
from minio import Minio
from minio.error import S3Error

# ========== CONFIG ==========
DEFAULT_INPUT = "data/raw/invoices_AR.csv"
DEFAULT_BUCKET = "sme-lake"
DEFAULT_BRONZE_RAW = "bronze/raw/invoices_AR/"
DEFAULT_BRONZE_SOURCE = "bronze/source/invoices_AR/"

MINIO_ENDPOINT = os.getenv("MINIO_HOST", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")

# ========== INGEST FUNCTION ==========
def ingest_invoices_ar(input_path, bucket, bronze_raw, bronze_source):
    print(f"[INFO] Reading {input_path} ...")
    df = pd.read_csv(input_path)
    print(f"[INFO] Loaded {len(df):,} rows, columns: {list(df.columns)}")

    # Save as Parquet
    parquet_path = input_path.replace(".csv", ".parquet")
    df.to_parquet(parquet_path, index=False)
    print(f"[INFO] Saved Parquet: {parquet_path}")

    # Connect MinIO
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )
    # Ensure bucket exists
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    # Upload Parquet to bronze/raw
    raw_obj = bronze_raw + os.path.basename(parquet_path)
    print(f"[INFO] Uploading Parquet to s3://{bucket}/{raw_obj}")
    client.fput_object(bucket, raw_obj, parquet_path)

    print("[SUCCESS] Ingested invoices_AR to Bronze (raw Parquet only)!")

# ========== MAIN ==========
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--bronze-raw", default=DEFAULT_BRONZE_RAW)
    parser.add_argument("--bronze-source", default=DEFAULT_BRONZE_SOURCE)
    args = parser.parse_args()

    ingest_invoices_ar(
        input_path=args.input,
        bucket=args.bucket,
        bronze_raw=args.bronze_raw,
        bronze_source=args.bronze_source
    )
