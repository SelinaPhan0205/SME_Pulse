"""
Test script để kiểm tra kết nối Trino và đọc data
"""
import sys
sys.path.insert(0, '/opt/ops/ml/UC09-forecasting')

from utils import get_trino_connector
import pandas as pd

def test_connection():
    print("🔍 Testing Trino connection...")
    try:
        conn = get_trino_connector()
        print("✅ Connection successful!")
        
        # Test query
        print("\n📊 Testing query on ml_training_cashflow_fcst...")
        query = "SELECT COUNT(*) as row_count FROM sme_lake.silver.ml_training_cashflow_fcst"
        df = pd.read_sql(query, conn)
        print(f"✅ Query successful! Rows: {df['row_count'].iloc[0]}")
        
        # Test reading full data
        print("\n📊 Reading full dataset...")
        query = "SELECT * FROM sme_lake.silver.ml_training_cashflow_fcst LIMIT 5"
        df = pd.read_sql(query, conn)
        print(f"✅ Loaded {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        print("\nSample data:")
        print(df.head())
        
        conn.close()
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
