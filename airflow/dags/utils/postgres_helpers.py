"""
PostgreSQL Database Helper Functions
Utilities for extracting data from App DB (postgres_application_db)
"""
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from io import BytesIO

logger = logging.getLogger(__name__)


def get_app_db_connection_params() -> Dict[str, str]:
    """
    Get connection parameters for Application Database (OLTP)
    
    Returns:
        Dict with host, port, database, user, password
    """
    return {
        'host': os.getenv('BACKEND_DB_HOST', 'postgres_application_db'),
        'port': int(os.getenv('BACKEND_DB_PORT', '5432')),
        'database': os.getenv('BACKEND_DB_NAME', 'sme_pulse_oltp'),
        'user': os.getenv('BACKEND_DB_USER', 'postgres'),
        'password': os.getenv('BACKEND_DB_PASSWORD', 'postgres')
    }


def extract_incremental_data(
    table_name: str,
    schema: str = 'finance',
    incremental_column: str = 'updated_at',
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Extract incremental data from Application Database
    
    Args:
        table_name: Table name (e.g., 'ar_invoices', 'payments')
        schema: Schema name (default: 'finance')
        incremental_column: Column for incremental loading (default: 'updated_at')
        start_date: Start date for extraction (default: yesterday)
        end_date: End date for extraction (default: today)
    
    Returns:
        DataFrame with extracted data
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        logger.error("psycopg2 not installed. Install via: pip install psycopg2-binary")
        raise
    
    conn_params = get_app_db_connection_params()
    
    # Default to yesterday if no start_date provided
    if start_date is None:
        start_date = datetime.now() - timedelta(days=1)
    if end_date is None:
        end_date = datetime.now()
    
    logger.info(f"Extracting {schema}.{table_name} from {start_date} to {end_date}")
    
    # Connect to database
    conn = psycopg2.connect(**conn_params)
    
    try:
        # Build query
        query = f"""
        SELECT * 
        FROM {schema}.{table_name}
        WHERE {incremental_column} >= %s 
          AND {incremental_column} < %s
        ORDER BY {incremental_column}
        """
        
        # Execute query
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (start_date, end_date))
            rows = cur.fetchall()
        
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        
        logger.info(f"✅ Extracted {len(df)} rows from {schema}.{table_name}")
        
        return df
        
    finally:
        conn.close()


def save_to_minio_bronze(
    df: pd.DataFrame,
    table_name: str,
    execution_date: str,
    minio_config: Dict
) -> str:
    """
    Save DataFrame to MinIO Bronze layer as Parquet
    
    Args:
        df: DataFrame to save
        table_name: Table name (e.g., 'ar_invoices')
        execution_date: Execution date string (YYYY-MM-DD)
        minio_config: MinIO configuration dict
    
    Returns:
        S3 path where file was saved
    """
    try:
        import boto3
        from botocore.client import Config
    except ImportError:
        logger.error("boto3 not installed. Install via: pip install boto3")
        raise
    
    if df.empty:
        logger.warning(f"⚠️ No data to save for {table_name} on {execution_date}")
        return ""
    
    # Initialize MinIO client
    s3_client = boto3.client(
        's3',
        endpoint_url=f"http://{minio_config['host']}:{minio_config['port']}",
        aws_access_key_id=minio_config['access_key'],
        aws_secret_access_key=minio_config['secret_key'],
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )
    
    # Convert DataFrame to Parquet bytes
    parquet_buffer = BytesIO()
    df.to_parquet(parquet_buffer, engine='pyarrow', compression='snappy', index=False)
    parquet_buffer.seek(0)
    
    # Define S3 path
    bucket = minio_config['bucket']
    s3_key = f"bronze/app_db/{table_name}/{execution_date}.parquet"
    
    # Upload to MinIO
    s3_client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=parquet_buffer.getvalue(),
        ContentType='application/octet-stream'
    )
    
    s3_path = f"s3a://{bucket}/{s3_key}"
    logger.info(f"✅ Saved {len(df)} rows to {s3_path}")
    
    return s3_path


def validate_app_db_connection() -> Dict[str, any]:
    """
    Validate connection to Application Database
    
    Returns:
        Dict with status, message, version
    """
    try:
        import psycopg2
    except ImportError:
        return {
            'status': 'error',
            'message': 'psycopg2 not installed'
        }
    
    conn_params = get_app_db_connection_params()
    
    try:
        conn = psycopg2.connect(**conn_params)
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
        
        conn.close()
        
        return {
            'status': 'healthy',
            'message': 'Connection successful',
            'version': version,
            'database': conn_params['database']
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


def get_table_row_count(table_name: str, schema: str = 'finance') -> int:
    """
    Get row count for a table
    
    Args:
        table_name: Table name
        schema: Schema name
    
    Returns:
        Row count
    """
    try:
        import psycopg2
    except ImportError:
        logger.error("psycopg2 not installed")
        return 0
    
    conn_params = get_app_db_connection_params()
    conn = psycopg2.connect(**conn_params)
    
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {schema}.{table_name}")
            count = cur.fetchone()[0]
        return count
    finally:
        conn.close()
