"""Celery tasks for background export jobs"""

import logging
import pandas as pd
import os
from datetime import datetime
from sqlalchemy import text, create_engine
from app.core.celery_config import celery_app
from app.core.minio_client import minio_client
from app.modules.analytics.services.export_excel_service import excel_service
from app.core.config import settings

logger = logging.getLogger(__name__)

# Trino connection string (for data warehouse queries)
TRINO_HOST = os.getenv("TRINO_HOST", "trino")
TRINO_PORT = int(os.getenv("TRINO_PORT", "8080"))
TRINO_USER = "trino"
TRINO_CATALOG = "sme_lake"
TRINO_SCHEMA = "silver"

# PostgreSQL fallback for when Trino is not available
# Use sync connection URL for pandas
PG_DATABASE_URL = settings.DATABASE_URL_SYNC

def get_trino_connection():
    """Create Trino SQL connection"""
    import trino
    return trino.dbapi.connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user=TRINO_USER,
        catalog=TRINO_CATALOG,
        schema=TRINO_SCHEMA,
    )

def get_postgres_engine():
    """Create PostgreSQL engine for fallback queries"""
    return create_engine(PG_DATABASE_URL)

def query_with_fallback(trino_query: str, postgres_query: str, use_postgres: bool = False):
    """
    Try Trino first, fall back to PostgreSQL if Trino is unavailable.
    
    Args:
        trino_query: SQL query for Trino
        postgres_query: SQL query for PostgreSQL
        use_postgres: Force PostgreSQL fallback
        
    Returns:
        pandas DataFrame
    """
    if not use_postgres:
        try:
            conn = get_trino_connection()
            df = pd.read_sql(trino_query, conn)
            conn.close()
            logger.info("✅ Query executed via Trino")
            return df
        except Exception as e:
            logger.warning(f"⚠️ Trino unavailable, falling back to PostgreSQL: {e}")
    
    # Fallback to PostgreSQL
    engine = get_postgres_engine()
    df = pd.read_sql(postgres_query, engine)
    engine.dispose()
    logger.info("✅ Query executed via PostgreSQL fallback")
    return df

@celery_app.task(bind=True, name="export_ar_aging")
def export_ar_aging(self, org_id: int) -> dict:
    """
    Background task to export AR aging report
    
    Args:
        org_id: Organization ID
        
    Returns:
        dict with status and file_url
    """
    try:
        # Update job status to processing
        self.update_state(state="PROGRESS", meta={"status": "processing", "progress": 25})
        logger.info(f"📊 Exporting AR Aging for org_id={org_id}")
        
        # Query for Trino
        trino_query = f"""
        SELECT 
            payment_id,
            business_code,
            payment_date_formatted,
            payment_amount,
            payment_method_code,
            reference_no,
            status,
            updated_at
        FROM {TRINO_CATALOG}.{TRINO_SCHEMA}.stg_app_payments
        ORDER BY updated_at DESC
        """
        
        # Fallback query for PostgreSQL - AR Invoices
        # Tables are in 'finance' and 'core' schemas
        postgres_query = f"""
        SELECT 
            i.id as invoice_id,
            i.invoice_no,
            c.name as customer_name,
            i.issue_date,
            i.due_date,
            i.total_amount,
            i.paid_amount,
            i.total_amount - i.paid_amount as remaining_amount,
            i.status,
            CASE 
                WHEN i.due_date < CURRENT_DATE AND i.status NOT IN ('paid', 'cancelled') 
                THEN CURRENT_DATE - i.due_date 
                ELSE 0 
            END as days_overdue,
            CASE 
                WHEN CURRENT_DATE - i.due_date <= 30 THEN '0-30 days'
                WHEN CURRENT_DATE - i.due_date <= 60 THEN '31-60 days'
                WHEN CURRENT_DATE - i.due_date <= 90 THEN '61-90 days'
                ELSE '90+ days'
            END as aging_bucket,
            i.updated_at
        FROM finance.ar_invoices i
        LEFT JOIN core.customers c ON i.customer_id = c.id
        WHERE i.org_id = {org_id}
        ORDER BY i.due_date ASC
        """
        
        df = query_with_fallback(trino_query, postgres_query)
        
        logger.info(f"✅ Loaded {len(df)} records")
        self.update_state(state="PROGRESS", meta={"status": "generating_excel", "progress": 50})
        
        # Generate Excel file
        file_path = excel_service.export_ar_aging(df, org_id)
        logger.info(f"✅ Generated Excel: {file_path}")
        
        self.update_state(state="PROGRESS", meta={"status": "uploading_file", "progress": 75})
        
        # Try MinIO upload, fallback to local file URL
        try:
            filename = os.path.basename(file_path)
            object_name = f"exports/ar_aging/{filename}"
            result = minio_client.upload_file(file_path, object_name)
            file_url = result["file_url"]
            logger.info(f"✅ Uploaded to MinIO: {object_name}")
            
            # Clean up local file
            os.remove(file_path)
        except Exception as upload_err:
            logger.warning(f"⚠️ MinIO upload failed, keeping local file: {upload_err}")
            file_url = f"file://{file_path}"
        
        return {
            "status": "completed",
            "file_url": file_url,
            "records": len(df),
            "job_id": self.request.id,
        }
        
    except Exception as e:
        logger.error(f"❌ Export AR Aging failed: {e}")
        return {
            "status": "failed",
            "error_message": str(e),
            "job_id": self.request.id
        }

@celery_app.task(bind=True, name="export_ap_aging")
def export_ap_aging(self, org_id: int) -> dict:
    """
    Background task to export AP aging report
    
    Args:
        job_id: Export job ID
        org_id: Organization ID
        
    Returns:
        dict with status and file_url
    """
    try:
        # Update job status to processing
        self.update_state(state="PROGRESS", meta={"status": "processing", "progress": 25})
        logger.info(f"📊 Exporting AP Aging for org_id={org_id}")
        
        # Query for Trino
        trino_query = f"""
        SELECT 
            payment_id,
            business_code,
            payment_date_formatted,
            payment_amount,
            payment_method_code,
            reference_no,
            status
        FROM {TRINO_CATALOG}.{TRINO_SCHEMA}.stg_app_payments
        ORDER BY updated_at DESC
        """
        
        # Fallback query for PostgreSQL - AP Bills
        postgres_query = f"""
        SELECT 
            b.id as bill_id,
            b.bill_no,
            s.name as supplier_name,
            b.issue_date,
            b.due_date,
            b.total_amount,
            b.paid_amount,
            b.total_amount - b.paid_amount as remaining_amount,
            b.status,
            CASE 
                WHEN b.due_date < CURRENT_DATE AND b.status NOT IN ('paid', 'cancelled') 
                THEN CURRENT_DATE - b.due_date 
                ELSE 0 
            END as days_overdue,
            CASE 
                WHEN CURRENT_DATE - b.due_date <= 30 THEN '0-30 days'
                WHEN CURRENT_DATE - b.due_date <= 60 THEN '31-60 days'
                WHEN CURRENT_DATE - b.due_date <= 90 THEN '61-90 days'
                ELSE '90+ days'
            END as aging_bucket,
            b.updated_at
        FROM finance.ap_bills b
        LEFT JOIN core.suppliers s ON b.supplier_id = s.id
        WHERE b.org_id = {org_id}
        ORDER BY b.due_date ASC
        """
        
        df = query_with_fallback(trino_query, postgres_query)
        
        logger.info(f"✅ Loaded {len(df)} AP payments")
        self.update_state(state="PROGRESS", meta={"status": "generating_excel", "progress": 50})
        
        # Generate Excel file
        file_path = excel_service.export_ap_aging(df, org_id)
        logger.info(f"✅ Generated Excel: {file_path}")
        
        self.update_state(state="PROGRESS", meta={"status": "uploading_file", "progress": 75})
        
        # Upload to MinIO
        filename = os.path.basename(file_path)
        object_name = f"exports/ap_aging/{filename}"
        result = minio_client.upload_file(file_path, object_name)
        
        logger.info(f"✅ Uploaded to MinIO: {object_name}")
        
        # Clean up local file
        os.remove(file_path)
        logger.info(f"✅ Cleaned up local file")
        
        return {
            "status": "completed",
            "file_url": result["file_url"],
            "object_name": result["object_name"],
            "records": len(df),
        }
        
    except Exception as e:
        logger.error(f"❌ Export AP Aging failed: {e}")
        return {
            "status": "failed",
            "error_message": str(e),
            "job_id": self.request.id
        }

@celery_app.task(bind=True, name="export_cashflow_forecast")
def export_cashflow_forecast(self, org_id: int) -> dict:
    """
    Background task to export cashflow forecast
    
    Args:
        job_id: Export job ID
        org_id: Organization ID
        
    Returns:
        dict with status and file_url
    """
    try:
        # Update job status to processing
        self.update_state(state="PROGRESS", meta={"status": "processing", "progress": 25})
        logger.info(f"📊 Exporting Cashflow Forecast for org_id={org_id}")
        
        # Query for Trino - Combined AR + Payments for cashflow
        trino_query = f"""
        SELECT 
            'AR' as type,
            invoice_id as id,
            baseline_create_date as date,
            total_open_amount as amount
        FROM {TRINO_CATALOG}.{TRINO_SCHEMA}.stg_app_ar_invoices
        UNION ALL
        SELECT 
            'Payment' as type,
            payment_id as id,
            payment_date_formatted as date,
            payment_amount as amount
        FROM {TRINO_CATALOG}.{TRINO_SCHEMA}.stg_app_payments
        ORDER BY date DESC
        """
        
        # Fallback query for PostgreSQL - Cashflow Forecast
        # Note: payments table doesn't have payment_type, using amount sign to determine direction
        postgres_query = f"""
        SELECT 
            'AR_Invoice' as type,
            i.id::text as id,
            i.due_date as date,
            (i.total_amount - i.paid_amount) as amount,
            'inflow' as direction
        FROM finance.ar_invoices i
        WHERE i.org_id = {org_id} AND i.status NOT IN ('paid', 'cancelled')
        UNION ALL
        SELECT 
            'AP_Bill' as type,
            b.id::text as id,
            b.due_date as date,
            (b.total_amount - b.paid_amount) as amount,
            'outflow' as direction
        FROM finance.ap_bills b
        WHERE b.org_id = {org_id} AND b.status NOT IN ('paid', 'cancelled')
        UNION ALL
        SELECT 
            'Payment' as type,
            p.id::text as id,
            p.transaction_date as date,
            p.amount,
            'inflow' as direction
        FROM finance.payments p
        WHERE p.org_id = {org_id}
        ORDER BY date ASC
        """
        
        df = query_with_fallback(trino_query, postgres_query)
        
        logger.info(f"✅ Loaded {len(df)} forecast records")
        self.update_state(state="PROGRESS", meta={"status": "generating_excel", "progress": 50})
        
        # Generate Excel file
        file_path = excel_service.export_cashflow_forecast(df, org_id)
        logger.info(f"✅ Generated Excel: {file_path}")
        
        self.update_state(state="PROGRESS", meta={"status": "uploading_file", "progress": 75})
        
        # Upload to MinIO
        filename = os.path.basename(file_path)
        object_name = f"exports/cashflow/{filename}"
        result = minio_client.upload_file(file_path, object_name)
        
        logger.info(f"✅ Uploaded to MinIO: {object_name}")
        
        # Clean up local file
        os.remove(file_path)
        logger.info(f"✅ Cleaned up local file")
        
        return {
            "status": "completed",
            "file_url": result["file_url"],
            "object_name": result["object_name"],
            "records": len(df),
        }
        
    except Exception as e:
        logger.error(f"❌ Export Cashflow Forecast failed: {e}")
        return {
            "status": "failed",
            "error_message": str(e),
            "job_id": self.request.id
        }
