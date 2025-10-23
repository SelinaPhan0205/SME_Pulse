#!/usr/bin/env python3
"""
Silver Layer - Load Parquet from Bronze to Iceberg
===================================================
Purpose: Read Parquet files from Bronze and insert into Silver Iceberg table
Flow: Bronze Parquet → Silver Iceberg (via batch INSERT)
"""

import boto3
from botocore.client import Config
import pandas as pd
from trino.dbapi import connect
from datetime import datetime
from io import BytesIO

# ==================== CONFIG ====================
MINIO_ENDPOINT = "http://minio:9000"
MINIO_ACCESS_KEY = "minio"
MINIO_SECRET_KEY = "minio123"
BRONZE_BUCKET = "bronze"
BRONZE_PREFIX = "raw/kaggle_vietnam_retail/sales_transactions/ingest_date=2025-10-22/parquet/"

TRINO_HOST = "trino"
TRINO_PORT = 8080
TRINO_USER = "airflow"

# ==================== CLIENTS ====================
s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

trino_conn = connect(
    host=TRINO_HOST,
    port=TRINO_PORT,
    user=TRINO_USER,
    catalog='iceberg',
    schema='silver'
)


def list_parquet_files():
    """List all Parquet files in Bronze"""
    response = s3_client.list_objects_v2(
        Bucket=BRONZE_BUCKET,
        Prefix=BRONZE_PREFIX
    )
    
    parquet_files = [
        obj['Key'] for obj in response.get('Contents', [])
        if obj['Key'].endswith('.parquet')
    ]
    
    return parquet_files


def load_parquet_to_silver(parquet_key: str):
    """Load one Parquet file into Silver Iceberg table"""
    
    print(f"\n📂 Processing: {parquet_key.split('/')[-1]}")
    
    # Download Parquet from S3
    obj = s3_client.get_object(Bucket=BRONZE_BUCKET, Key=parquet_key)
    parquet_buffer = BytesIO(obj['Body'].read())
    
    # Read Parquet with Pandas
    df = pd.read_parquet(parquet_buffer)
    row_count = len(df)
    print(f"   📊 Read {row_count:,} rows from Parquet")
    
    # Add loaded_at timestamp
    df['loaded_at'] = datetime.now()
    
    # Batch insert into Iceberg (500 rows per batch)
    batch_size = 500
    total_inserted = 0
    
    cursor = trino_conn.cursor()
    
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        
        # Build VALUES clause
        values_list = []
        for _, row in batch.iterrows():
            values = (
                f"('{row['month']}', '{row['week']}', '{row['site']}', "
                f"'{row['branch_id']}', '{row['channel_id']}', "
                f"'{row['distribution_channel']}', '{row['distribution_channel_code']}', "
                f"{row['sold_quantity']}, {row['cost_price']}, {row['net_price']}, "
                f"'{row['customer_id']}', '{row['product_id']}', "
                f"TIMESTAMP '{row['loaded_at'].strftime('%Y-%m-%d %H:%M:%S')}')"
            )
            values_list.append(values)
        
        values_str = ',\n'.join(values_list)
        
        sql = f"""
        INSERT INTO iceberg.silver.stg_transactions
        (month, week, site, branch_id, channel_id, distribution_channel, 
         distribution_channel_code, sold_quantity, cost_price, net_price, 
         customer_id, product_id, loaded_at)
        VALUES {values_str}
        """
        
        cursor.execute(sql)
        total_inserted += len(batch)
        
        if (i + batch_size) % 5000 == 0:
            print(f"   ✅ Inserted {total_inserted:,}/{row_count:,} rows...")
    
    print(f"   ✅ Completed: {total_inserted:,} rows inserted into Silver")
    cursor.close()


def main():
    print("🚀 Silver Layer - Load from Bronze Parquet")
    print("=" * 70)
    
    # List Parquet files
    parquet_files = list_parquet_files()
    print(f"📁 Found {len(parquet_files)} Parquet files in Bronze")
    
    # Process each file
    for parquet_key in parquet_files:
        try:
            load_parquet_to_silver(parquet_key)
        except Exception as e:
            print(f"❌ Error processing {parquet_key}: {e}")
    
    # Verify
    cursor = trino_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM iceberg.silver.stg_transactions")
    total_rows = cursor.fetchone()[0]
    cursor.close()
    
    print("\n" + "=" * 70)
    print(f"📊 Total rows in Silver: {total_rows:,}")
    print("✅ Silver layer load completed!")
    
    trino_conn.close()


if __name__ == "__main__":
    main()
