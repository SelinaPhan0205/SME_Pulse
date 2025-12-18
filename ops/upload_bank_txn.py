"""
Upload Bank Transactions Parquet file to MinIO
---------------------------------------------
Single-file ingestion for Bronze/raw/bank_txn_ layer.

Usage:
    python ops/upload_bank_txn.py

Environment Variables:
    MINIO_ENDPOINT      MinIO endpoint (default: http://sme-minio:9000 for Docker, http://localhost:9000 for local)
    MINIO_ACCESS_KEY    Access key (default: minio)
    MINIO_SECRET_KEY    Secret key (default: minio123)
    BRONZE_BUCKET       Bronze bucket name (default: sme-pulse)
"""

import os
import sys
import boto3
from datetime import datetime
from pathlib import Path


class BankTxnIngestionMinIO:
    """Upload single Parquet file to Bronze/raw/bank_txn_"""

    def __init__(self):
        """Initialize MinIO connection"""
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'http://sme-minio:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY', 'minio')
        self.secret_key = os.getenv('MINIO_SECRET_KEY', 'minio123')
        self.bronze_bucket = os.getenv('BRONZE_BUCKET', 'sme-pulse')

        self.s3_client = None

    def connect(self):
        """Establish MinIO connection"""
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
        """Create bucket if not exists"""
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

    def upload_parquet(self, file_path, prefix="bank_txn"):
        """Upload the Parquet file to MinIO under bronze/raw"""
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return False

        file_name = file_path.name
        # 👉 Đường dẫn đích: bronze/raw/bank_txn_/Bank_Transactions.parquet
        s3_key = f"bronze/raw/{prefix}/{file_name}"

        print(f"\n{'='*70}")
        print(f"🚀 UPLOADING PARQUET FILE TO MINIO")
        print(f"{'='*70}")
        print(f"📄 Local file : {file_path}")
        print(f"🎯 Target path: s3://{self.bronze_bucket}/{s3_key}")
        print(f"{'='*70}\n")

        try:
            with open(file_path, "rb") as f:
                data = f.read()
                size_mb = len(data) / (1024 * 1024)
                self.s3_client.put_object(
                    Bucket=self.bronze_bucket,
                    Key=s3_key,
                    Body=data,
                    ContentType='application/x-parquet',
                    Metadata={
                        'source_file': file_name,
                        'ingested_at': datetime.utcnow().isoformat(),
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
            return False


def main():
    # ✅ Đường dẫn thật của cậu
    file_path = "/opt/data/Bank_Transactions/Bank_Transactions.parquet"

    ingestion = BankTxnIngestionMinIO()

    if not ingestion.connect():
        sys.exit(1)

    if not ingestion.create_bucket():
        sys.exit(1)

    success = ingestion.upload_parquet(file_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

