"""
PostgreSQL helpers for extracting transactional data from App DB
"""
import pandas as pd
import logging
from io import BytesIO
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta
import pyarrow as pa
import pyarrow.parquet as pq
from minio import Minio
from pathlib import Path

logger = logging.getLogger(__name__)


def get_postgres_connection(postgres_config):
    """
    Create PostgreSQL connection
    
    Args:
        postgres_config: Dict with keys {host, port, database, user, password}
    
    Returns:
        psycopg2 connection object
    """
    try:
        conn = psycopg2.connect(
            host=postgres_config.get('host', 'localhost'),
            port=postgres_config.get('port', 5432),
            database=postgres_config.get('database', 'app_db'),
            user=postgres_config.get('user', 'postgres'),
            password=postgres_config.get('password', '')
        )
        logger.info(f"✅ Connected to PostgreSQL: {postgres_config.get('host')}")
        return conn
    except psycopg2.Error as e:
        logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
        raise


def extract_ar_invoices(postgres_config, last_run_time=None):
    """
    Extract AR invoices from PostgreSQL
    
    Args:
        postgres_config: PostgreSQL connection config
        last_run_time: Optional - only extract records updated after this time (incremental load)
    
    Returns:
        pandas DataFrame with AR invoices
    """
    conn = get_postgres_connection(postgres_config)
    
    try:
        # Build query
        query = """
        SELECT 
            id,
            org_id,
            invoice_no,
            customer_id,
            issue_date,
            due_date,
            total_amount,
            paid_amount,
            status,
            notes,
            created_at,
            updated_at
        FROM finance.ar_invoices
        WHERE 1=1
        """
        
        # Add incremental filter if last_run_time provided
        if last_run_time:
            query += f"\n        AND updated_at >= '{last_run_time}'"
        
        query += "\n        ORDER BY updated_at DESC"
        
        logger.info(f"Executing query: {query}")
        
        # Read into pandas DataFrame
        df = pd.read_sql(query, conn)
        logger.info(f"✅ Extracted {len(df)} AR invoices")
        
        return df
    
    except Exception as e:
        logger.error(f"❌ Error extracting AR invoices: {e}")
        raise
    
    finally:
        conn.close()


def extract_payments(postgres_config, last_run_time=None):
    """
    Extract payments from PostgreSQL
    
    Args:
        postgres_config: PostgreSQL connection config
        last_run_time: Optional - only extract records updated after this time
    
    Returns:
        pandas DataFrame with payments
    """
    conn = get_postgres_connection(postgres_config)
    
    try:
        query = postgres_config.get('queries', {}).get('payments', """
        SELECT 
            id, org_id, transaction_date as payment_date, payment_method,
            amount, reference_code, notes,
            created_at, updated_at
        FROM finance.payments
        ORDER BY updated_at DESC
        """)
        
        logger.info(f"Executing query: {query}")
        
        df = pd.read_sql(query, conn)
        logger.info(f"✅ Extracted {len(df)} payments")
        
        return df
    
    except Exception as e:
        logger.error(f"❌ Error extracting payments: {e}")
        raise
    
    finally:
        conn.close()


def extract_payment_allocations(postgres_config, last_run_time=None):
    """
    Extract payment allocations from PostgreSQL
    
    Args:
        postgres_config: PostgreSQL connection config
        last_run_time: Optional - only extract records updated after this time
    
    Returns:
        pandas DataFrame with payment allocations
    """
    conn = get_postgres_connection(postgres_config)
    
    try:
        query = postgres_config.get('queries', {}).get('payment_allocations', """
        SELECT 
            id, org_id, payment_id, ar_invoice_id,
            allocated_amount as amount, created_at as allocation_date, notes,
            created_at, updated_at
        FROM finance.payment_allocations
        ORDER BY updated_at DESC
        """)
        
        logger.info(f"Executing query: {query}")
        
        df = pd.read_sql(query, conn)
        logger.info(f"✅ Extracted {len(df)} payment allocations")
        
        return df
    
    except Exception as e:
        logger.error(f"❌ Error extracting payment allocations: {e}")
        raise
    
    finally:
        conn.close()


def save_to_parquet_minio(df, minio_config, bucket, object_path):
    """
    Save pandas DataFrame to Parquet in MinIO
    
    Args:
        df: pandas DataFrame
        minio_config: MinIO config dict {endpoint, access_key, secret_key}
        bucket: MinIO bucket name (e.g., 'sme-lake')
        object_path: S3 path (e.g., 'bronze/app_db/ar_invoices/2025-11-22T10:30:00.parquet')
    
    Returns:
        object_path if successful
    """
    try:
        # Initialize MinIO client
        client = Minio(
            minio_config.get('endpoint', 'minio:9000'),
            access_key=minio_config.get('access_key'),
            secret_key=minio_config.get('secret_key'),
            secure=False
        )
        
        # Convert to Parquet
        table = pa.Table.from_pandas(df)
        parquet_buffer = BytesIO()
        pq.write_table(table, parquet_buffer)
        parquet_buffer.seek(0)
        
        # Upload to MinIO
        client.put_object(
            bucket_name=bucket,
            object_name=object_path,
            data=parquet_buffer,
            length=len(parquet_buffer.getvalue()),
            content_type='application/octet-stream'
        )
        
        logger.info(f"✅ Saved to MinIO: s3a://{bucket}/{object_path}")
        return object_path
    
    except Exception as e:
        logger.error(f"❌ Error saving to MinIO: {e}")
        raise


def extract_and_load_transactional_data(postgres_config, minio_config, bucket='sme-pulse', last_run_time=None, **context):
    """
    Main function: Extract AR invoices, payments, and allocations from App DB
    and save to MinIO Bronze layer
    
    Args:
        postgres_config: PostgreSQL connection config
        minio_config: MinIO config
        bucket: MinIO bucket name (default: sme-pulse)
        last_run_time: Optional - only extract records updated after this time (for incremental load)
        context: Airflow context (for XCom, logging, etc)
    
    Returns:
        dict with extraction results
    """
    logger.info("🔄 Starting extraction of transactional data from App DB...")
    
    if last_run_time:
        logger.info(f"📅 Incremental load: extracting records updated after {last_run_time}")
    else:
        logger.info("📦 Full load: extracting all records")
    
    try:
        # Generate timestamp for partitioning
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Extract AR invoices
        logger.info("Extracting AR invoices...")
        df_invoices = extract_ar_invoices(postgres_config, last_run_time=last_run_time)
        if len(df_invoices) > 0:
            path_invoices = f"bronze/raw/app_db/ar_invoices/{timestamp}.parquet"
            save_to_parquet_minio(df_invoices, minio_config, bucket, path_invoices)
        else:
            logger.info("No new AR invoices to load")
        
        # Extract payments
        logger.info("Extracting payments...")
        df_payments = extract_payments(postgres_config, last_run_time=last_run_time)
        if len(df_payments) > 0:
            path_payments = f"bronze/raw/app_db/payments/{timestamp}.parquet"
            save_to_parquet_minio(df_payments, minio_config, bucket, path_payments)
        else:
            logger.info("No new payments to load")
        
        # Extract payment allocations
        logger.info("Extracting payment allocations...")
        df_allocations = extract_payment_allocations(postgres_config, last_run_time=last_run_time)
        if len(df_allocations) > 0:
            path_allocations = f"bronze/raw/app_db/payment_allocations/{timestamp}.parquet"
            save_to_parquet_minio(df_allocations, minio_config, bucket, path_allocations)
        else:
            logger.info("No new payment allocations to load")
        
        results = {
            'status': 'success',
            'timestamp': timestamp,
            'ar_invoices_count': len(df_invoices),
            'payments_count': len(df_payments),
            'payment_allocations_count': len(df_allocations),
            'total_records': len(df_invoices) + len(df_payments) + len(df_allocations),
            'load_type': 'incremental' if last_run_time else 'full'
        }
        
        logger.info(f"✅ Extraction completed: {results}")
        
        # Push to XCom for downstream tasks
        if context and 'ti' in context:
            context['ti'].xcom_push(key='extraction_results', value=results)
        
        return results
    
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        raise

