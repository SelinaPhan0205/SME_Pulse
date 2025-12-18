#!/usr/bin/env python3
"""
Quick check for ML anomaly tables in Trino
"""
import sys
sys.path.insert(0, '/opt/ops/ML-anomaly_detection')

import trino

def get_trino_connector():
    """Tạo kết nối Trino/Iceberg."""
    conn = trino.dbapi.connect(
        host="trino",
        port=8080,
        user="python_script",
        catalog="sme_pulse",
        schema="gold",
    )
    return conn

try:
    cursor = get_trino_connector().cursor()
    
    # Check ml_anomaly_alerts table
    print("\n" + "="*60)
    print("1️⃣ CHECK ml_anomaly_alerts TABLE")
    print("="*60)
    try:
        cursor.execute('SELECT COUNT(*) as count FROM "sme_pulse".gold.ml_anomaly_alerts')
        result = cursor.fetchone()
        count = result[0] if result else 0
        print(f"✅ Table EXISTS! Records: {count}")
        
        # Get sample data
        cursor.execute('SELECT alert_id, txn_date, amount_vnd, severity FROM "sme_pulse".gold.ml_anomaly_alerts LIMIT 5')
        samples = cursor.fetchall()
        print("\n📋 Sample Data:")
        for row in samples:
            print(f"  - Alert: {row[0]}, Date: {row[1]}, Amount: {row[2]}, Severity: {row[3]}")
    except Exception as e:
        print(f"❌ Table NOT found: {e}")
    
    # Check ml_anomaly_statistics table
    print("\n" + "="*60)
    print("2️⃣ CHECK ml_anomaly_statistics TABLE")
    print("="*60)
    try:
        cursor.execute('SELECT COUNT(*) as count FROM "sme_pulse".gold.ml_anomaly_statistics')
        result = cursor.fetchone()
        count = result[0] if result else 0
        print(f"✅ Table EXISTS! Records: {count}")
        
        # Get sample data
        cursor.execute('SELECT stat_date, total_transactions, anomaly_count, anomaly_percentage FROM "sme_pulse".gold.ml_anomaly_statistics LIMIT 5')
        samples = cursor.fetchall()
        print("\n📊 Sample Statistics:")
        for row in samples:
            print(f"  - Date: {row[0]}, Total: {row[1]}, Anomalies: {row[2]}, %: {row[3]:.2f}%")
    except Exception as e:
        print(f"❌ Table NOT found: {e}")
    
    print("\n" + "="*60)
    print("DONE!")
    print("="*60)

except Exception as e:
    print(f"❌ Connection Error: {e}")
    import traceback
    traceback.print_exc()

