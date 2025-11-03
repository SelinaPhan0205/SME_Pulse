#!/usr/bin/env python3
"""
Generate Trino CREATE TABLE from Parquet files in MinIO
"""

import sys
from pathlib import Path
from minio import Minio
import pyarrow.parquet as pq
import pyarrow as pa
import tempfile

# MinIO config
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin123"
MINIO_BUCKET = "sme-lake"

def parquet_to_trino_type(pa_type):
    """Convert PyArrow type to Trino SQL type"""
    type_str = str(pa_type)
    
    # Handle timestamp types
    if pa.types.is_timestamp(pa_type):
        return "TIMESTAMP"
    
    # Basic types
    mapping = {
        'int64': 'BIGINT',
        'int32': 'INTEGER',
        'float64': 'DOUBLE',
        'float32': 'REAL',
        'bool': 'BOOLEAN',
        'string': 'VARCHAR',
        'binary': 'VARBINARY',
        'date32': 'DATE',
        'date64': 'DATE',
    }
    
    # Check exact matches
    if type_str in mapping:
        return mapping[type_str]
    
    # Check type families
    if 'int' in type_str.lower():
        return 'BIGINT'
    if 'float' in type_str.lower() or 'double' in type_str.lower():
        return 'DOUBLE'
    if 'string' in type_str.lower():
        return 'VARCHAR'
    if 'timestamp' in type_str.lower():
        return 'TIMESTAMP'
    if 'date' in type_str.lower():
        return 'DATE'
    
    return 'VARCHAR'  # Default fallback

def generate_create_table_sql(object_path: str, table_name: str):
    """Generate CREATE TABLE SQL from Parquet schema"""
    print(f"\n{'='*70}")
    print(f"Processing: {object_path}")
    print(f"{'='*70}\n")
    
    # Connect MinIO
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )
    
    # Download to temp file
    tmp = tempfile.NamedTemporaryFile(suffix='.parquet', delete=False)
    tmp_path = tmp.name
    tmp.close()
    
    try:
        client.fget_object(MINIO_BUCKET, object_path, tmp_path)
        
        # Read schema
        table = pq.read_table(tmp_path)
        schema = table.schema
        
        print("PyArrow Schema:")
        for i, field in enumerate(schema):
            print(f"  {i+1:2d}. {field.name:35s} {field.type}")
        
        # Generate SQL
        print(f"\n\n-- Generated CREATE TABLE SQL:")
        print(f"-- ===================================================================")
        print(f"DROP TABLE IF EXISTS minio.default.{table_name};")
        print()
        print(f"CREATE TABLE minio.default.{table_name} (")
        
        columns = []
        max_name_len = max(len(field.name) for field in schema)
        
        for field in schema:
            trino_type = parquet_to_trino_type(field.type)
            columns.append(f"    {field.name.ljust(max_name_len)} {trino_type}")
        
        print(",\n".join(columns))
        
        print(")")
        print("WITH (")
        print("    format = 'PARQUET',")
        
        # Extract directory path (remove filename)
        dir_path = '/'.join(object_path.split('/')[:-1]) + '/'
        print(f"    external_location = 's3a://{MINIO_BUCKET}/{dir_path}'")
        print(");")
        print()
        print(f"-- Verify")
        print(f"SELECT COUNT(*) as total_rows FROM minio.default.{table_name};")
        print(f"SELECT * FROM minio.default.{table_name} LIMIT 5;")
        print(f"-- ===================================================================\n")
    finally:
        # Clean up temp file
        import os
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

if __name__ == "__main__":
    print("🔧 Generate Trino CREATE TABLE from Parquet\n")
    
    # Generate for both tables
    generate_create_table_sql(
        "bronze/raw/bank_txn_raw/bank_transactions.parquet",
        "bank_txn_raw"
    )
    
    generate_create_table_sql(
        "bronze/raw/shipments_payments_raw/shipments_payments.parquet",
        "shipments_payments_raw"
    )
