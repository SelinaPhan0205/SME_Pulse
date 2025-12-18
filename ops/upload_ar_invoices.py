"""
Upload AR Invoices CSV file to MinIO
---------------------------------------------
Single-file ingestion for Bronze/raw/ar_invoices layer.

Usage:
    python ops/upload_ar_invoices.py

Environment Variables:
    MINIO_ENDPOINT      MinIO endpoint (default: http://sme-minio:9000 for Docker, http://localhost:9000 for local)
    MINIO_ACCESS_KEY    Access key (default: minio)
    MINIO_SECRET_KEY    Secret key (default: minio123)
    BRONZE_BUCKET       Bronze bucket name (default: sme-pulse)
"""

import os
import sys
import boto3
import pandas as pd
from io import BytesIO
from datetime import datetime
from pathlib import Path


class ARInvoicesIngestionMinIO:
    """Upload AR Invoices CSV file → convert → Parquet → Bronze/raw/ar_invoices"""

    def __init__(self):
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'http://sme-minio:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY', 'minio')
        self.secret_key = os.getenv('MINIO_SECRET_KEY', 'minio123')
        self.bronze_bucket = os.getenv('BRONZE_BUCKET', 'sme-pulse')
        self.s3_client = None

    def connect(self):
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name='us-east-1'
            )
            self.s3_client.list_buckets()
            print(f"✅ Connected to MinIO: {self.endpoint}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to MinIO: {e}")
            return False

    def create_bucket(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bronze_bucket)
            print(f"✅ Bucket '{self.bronze_bucket}' exists")
        except:
            try:
                self.s3_client.create_bucket(Bucket=self.bronze_bucket)
                print(f"✅ Created bucket: {self.bronze_bucket}")
            except Exception as e:
                print(f"❌ Failed to create bucket: {e}")
                return False
        return True

    def upload_csv_as_parquet(self, file_path, prefix="ar_invoices"):
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return False

        file_name = file_path.stem + ".parquet"
        s3_key = f"bronze/raw/{prefix}/{file_name}"

        print(f"\n{'='*70}")
        print("🚀 UPLOADING AR INVOICES CSV TO MINIO")
        print(f"{'='*70}")
        print(f"📄 Local file : {file_path}")
        print(f"🎯 Target path: s3://{self.bronze_bucket}/{s3_key}")
        print(f"{'='*70}\n")

        try:
            df = pd.read_csv(file_path)
            print(f"✅ Loaded CSV: {len(df):,} rows × {len(df.columns)} cols")

            buffer = BytesIO()
            df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
            buffer.seek(0)
            size_mb = len(buffer.getvalue()) / (1024 * 1024)

            self.s3_client.put_object(
                Bucket=self.bronze_bucket,
                Key=s3_key,
                Body=buffer.getvalue(),
                ContentType='application/x-parquet',
                Metadata={
                    'source_file': file_path.name,
                    'ingested_at': datetime.utcnow().isoformat(),
                    'rows': str(len(df)),
                    'columns': str(len(df.columns)),
                    'size_mb': f"{size_mb:.2f}"
                }
            )
            print(f"✅ Uploaded successfully: {size_mb:.2f} MB → {s3_key}")
            print(f"🔗 View in MinIO Console:")
            print(f"   http://localhost:9001/browser/{self.bronze_bucket}/bronze/raw/{prefix}")
            print(f"{'='*70}")
            print("✅ INGESTION COMPLETE!")
            print(f"{'='*70}\n")
            return True
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            import traceback; traceback.print_exc()
            return False


def main():
    file_path = "/opt/data/AR_Invoices Dataset/dataset.csv"

    ingestion = ARInvoicesIngestionMinIO()

    if not ingestion.connect():
        sys.exit(1)

    if not ingestion.create_bucket():
        sys.exit(1)

    success = ingestion.upload_csv_as_parquet(file_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

