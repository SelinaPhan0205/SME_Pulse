#!/usr/bin/env python3
"""
Check Parquet Schema from MinIO
"""

import sys
from pathlib import Path
from minio import Minio
import pyarrow.parquet as pq
import tempfile

# MinIO config
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin123"
MINIO_BUCKET = "sme-lake"

def check_schema(object_path: str):
    """Download and check parquet schema"""
    print(f"\n{'='*70}")
    print(f"Checking: {object_path}")
    print(f"{'='*70}")
    
    # Connect MinIO
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )
    
    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        client.fget_object(MINIO_BUCKET, object_path, tmp.name)
        
        # Read schema
        parquet_file = pq.ParquetFile(tmp.name)
        schema = parquet_file.schema
        
        print(f"\nParquet Schema:")
        print(schema)
        
        print(f"\n\nColumn Details:")
        for i, field in enumerate(schema):
            print(f"{i+1:2d}. {field.name:30s} {field.type}")
        
        # Read sample data
        table = pq.read_table(tmp.name)
        df = table.to_pandas()
        print(f"\n\nData Shape: {df.shape}")
        print(f"\nFirst 3 rows:")
        print(df.head(3))
        
        print(f"\n\nData Types:")
        print(df.dtypes)

if __name__ == "__main__":
    print("🔍 Parquet Schema Checker\n")
    
    # Check both files
    check_schema("bronze/raw/bank_txn_raw/bank_transactions.parquet")
    check_schema("bronze/raw/shipments_payments_raw/shipments_payments.parquet")
