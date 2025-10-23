#!/usr/bin/env python3
"""
Get Parquet schema from S3 and generate CREATE TABLE statement
"""

import boto3
import pandas as pd
from io import BytesIO
import json

MINIO_ENDPOINT = "http://minio:9000"
MINIO_ACCESS_KEY = "minio"
MINIO_SECRET_KEY = "minio123"

s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name="us-east-1",
)

def get_parquet_schema(bucket, prefix):
    """Get first parquet file schema from S3"""
    try:
        # List parquet files
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        if "Contents" not in response:
            print(f"No files found in {prefix}")
            return None
        
        # Get first parquet file
        parquet_files = [obj["Key"] for obj in response["Contents"] if obj["Key"].endswith(".parquet")]
        if not parquet_files:
            print("No parquet files found")
            return None
        
        first_file = parquet_files[0]
        print(f"📖 Reading schema from: {first_file}")
        
        # Download file
        response = s3_client.get_object(Bucket=bucket, Key=first_file)
        df = pd.read_parquet(BytesIO(response["Body"].read()))
        
        print(f"\n📊 DataFrame shape: {df.shape}")
        print(f"📊 Columns: {len(df.columns)}")
        
        return df, first_file
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def pandas_to_hive_type(pandas_dtype):
    """Convert pandas dtype to Hive/Trino type"""
    dtype_str = str(pandas_dtype)
    
    if "int64" in dtype_str:
        return "BIGINT"
    elif "int32" in dtype_str or "int" in dtype_str:
        return "INTEGER"
    elif "float64" in dtype_str or "float" in dtype_str:
        return "DOUBLE"
    elif "bool" in dtype_str:
        return "BOOLEAN"
    elif "datetime" in dtype_str or "date" in dtype_str:
        return "DATE"
    elif "object" in dtype_str:
        return "STRING"
    else:
        return "STRING"

def generate_create_table_sql(df, table_name, external_location):
    """Generate CREATE TABLE statement"""
    
    sql_lines = [
        f"CREATE TABLE IF NOT EXISTS {table_name} (",
    ]
    
    cols = df.columns.tolist()
    for i, col in enumerate(cols):
        hive_type = pandas_to_hive_type(df[col].dtype)
        # Sanitize column name (replace spaces, special chars)
        clean_col = col.replace(" ", "_").replace("-", "_").lower()
        
        comma = "," if i < len(cols) - 1 else ""
        sql_lines.append(f"  {clean_col} {hive_type}{comma}")
    
    sql_lines.append(")")
    sql_lines.append(f"WITH (")
    sql_lines.append(f"  external_location = '{external_location}',")
    sql_lines.append(f"  format = 'PARQUET'")
    sql_lines.append(f");")
    
    return "\n".join(sql_lines)

def main():
    print("=" * 70)
    print("🔍 GETTING PARQUET SCHEMA FROM BRONZE")
    print("=" * 70)
    
    bucket = "bronze"
    prefix = "raw/sales_snapshot/"
    
    result = get_parquet_schema(bucket, prefix)
    if result is None:
        return
    
    df, file_key = result
    
    # Print sample data
    print("\n📋 SAMPLE DATA (first 3 rows):")
    print(df.head(3).to_string())
    
    # Print dtypes
    print("\n📊 DATA TYPES:")
    for col, dtype in df.dtypes.items():
        print(f"  {col}: {dtype}")
    
    # Generate SQL
    print("\n" + "=" * 70)
    print("🔨 GENERATED SQL:")
    print("=" * 70 + "\n")
    
    sql = generate_create_table_sql(
        df,
        "bronze.default.sales_snapshot_raw",
        "s3://bronze/raw/sales_snapshot/"
    )
    print(sql)
    
    # Save to file
    with open("create_external_table.sql", "w") as f:
        f.write(sql)
    print("\n✅ SQL saved to: create_external_table.sql")

if __name__ == "__main__":
    main()
