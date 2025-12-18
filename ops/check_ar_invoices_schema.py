"""
Check schema of AR Invoices Parquet file in MinIO
"""

import os
import boto3
import pyarrow.parquet as pq
from io import BytesIO

endpoint = os.getenv('MINIO_ENDPOINT', 'http://sme-minio:9000')
access_key = os.getenv('MINIO_ACCESS_KEY', 'minio')
secret_key = os.getenv('MINIO_SECRET_KEY', 'minio123')
bronze_bucket = os.getenv('BRONZE_BUCKET', 'sme-pulse')

s3_client = boto3.client(
    's3',
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name='us-east-1'
)

try:
    # Get Parquet file from MinIO
    response = s3_client.get_object(
        Bucket=bronze_bucket,
        Key='bronze/raw/ar_invoices/dataset.parquet'
    )
    
    # Read schema
    parquet_file = pq.read_table(BytesIO(response['Body'].read()))
    schema = parquet_file.schema
    
    print("=" * 80)
    print("📊 PARQUET FILE SCHEMA")
    print("=" * 80)
    print(schema)
    print("\n" + "=" * 80)
    print("Column Names and Types:")
    print("=" * 80)
    for i, field in enumerate(schema):
        print(f"{i+1:2d}. {field.name:30s} → {field.type}")
    
    print("\n" + "=" * 80)
    print(f"Total columns: {len(schema)}")
    print("=" * 80)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

