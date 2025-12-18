"""
UC10 - Anomaly Detection: Test Connection Script
=================================================
Kiểm tra kết nối Trino và độ sẵn sàng của dữ liệu fact_bank_txn
"""

import sys
sys.path.insert(0, '/opt')

from utils import get_trino_connector
import pandas as pd
import logging
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_connection():
    """
    Kiểm tra:
    1. Kết nối Trino
    2. Truy cập bảng fact_bank_txn
    3. Lấy dữ liệu mẫu
    4. Kiểm tra ngày bắt đầu huấn luyện
    """
    logger.info("=" * 80)
    logger.info("🔍 UC10 ANOMALY DETECTION - CONNECTION TEST")
    logger.info("=" * 80)
    
    try:
        # 1. Test kết nối
        logger.info("\n[1/4] Testing Trino connection...")
        conn = get_trino_connector()
        logger.info("✅ Trino connection successful!")
        
        # 2. Kiểm tra bảng fact_bank_txn
        logger.info("\n[2/4] Checking fact_bank_txn table...")
        query_check = "SELECT COUNT(*) as row_count FROM \"sme_pulse\".gold.fact_bank_txn"
        df_check = pd.read_sql(query_check, conn)
        row_count = df_check['row_count'].iloc[0]
        logger.info(f"✅ fact_bank_txn contains {row_count:,} rows")
        
        # 3. Lấy schema
        logger.info("\n[3/4] Reading table schema and sample data...")
        query_sample = """
        SELECT 
            txn_id,
            date_key,
            txn_date,
            txn_timestamp,
            currency_code,
            direction_in_out,
            counterparty_name,
            amount_vnd,
            is_inflow,
            is_large_transaction,
            transaction_category
        FROM "sme_pulse".gold.fact_bank_txn 
        LIMIT 10
        """
        df_sample = pd.read_sql(query_sample, conn)
        logger.info(f"✅ Schema verified! Columns: {list(df_sample.columns)}")
        logger.info(f"\n{df_sample.head(3).to_string()}")
        
        # 4. Lấy thống kê
        logger.info("\n[4/4] Getting data statistics...")
        query_stats = """
        SELECT
            DATE_TRUNC('day', txn_date) as txn_date_day,
            COUNT(*) as txn_count,
            COUNT(DISTINCT direction_in_out) as direction_types,
            SUM(amount_vnd) as total_amount_vnd,
            MIN(amount_vnd) as min_amount,
            MAX(amount_vnd) as max_amount,
            APPROX_PERCENTILE(ABS(amount_vnd), 0.95) as p95_amount
        FROM "sme_pulse".gold.fact_bank_txn
        GROUP BY DATE_TRUNC('day', txn_date)
        ORDER BY txn_date_day DESC
        LIMIT 7
        """
        df_stats = pd.read_sql(query_stats, conn)
        logger.info("\n📊 Last 7 days statistics:")
        logger.info(f"\n{df_stats.to_string()}")
        
        # 5. Kiểm tra date range
        query_date_range = """
        SELECT 
            MIN(txn_date) as min_date,
            MAX(txn_date) as max_date,
            COUNT(DISTINCT DATE(txn_date)) as distinct_days
        FROM "sme_pulse".gold.fact_bank_txn
        """
        df_date_range = pd.read_sql(query_date_range, conn)
        logger.info(f"\n📅 Date range: {df_date_range['min_date'].iloc[0]} to {df_date_range['max_date'].iloc[0]}")
        logger.info(f"   Distinct days: {df_date_range['distinct_days'].iloc[0]}")
        
        conn.close()
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ ALL TESTS PASSED! Ready for Anomaly Detection training.")
        logger.info("=" * 80)
        return True
        
    except Exception as e:
        logger.error(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        logger.error("\n" + "=" * 80)
        logger.error("❌ Connection test failed! Check logs above.")
        logger.error("=" * 80)
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

