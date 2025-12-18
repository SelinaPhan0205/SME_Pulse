import pandas as pd
import sqlite3
import os
from datetime import datetime

# Đọc 2 file CSV từ thư mục hiện tại
cashflow_csv = 'cashflow_forecast_result.csv'
anomaly_csv = 'anomaly_result.csv'

def format_date(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    return d.strftime('%B %d, %Y')

# Tạo database SQLite
db_file = 'mock_predictions.db'
conn = sqlite3.connect(db_file)

print("Converting CSV to SQLite...")

# Table 1: Cashflow Forecast
if os.path.exists(cashflow_csv):
    df_cashflow = pd.read_csv(cashflow_csv)
    df_cashflow['ds'] = df_cashflow['ds'].apply(format_date)
    df_cashflow.to_sql('cashflow_forecast', conn, if_exists='replace', index=False)
    print(f"✅ Đã tạo table 'cashflow_forecast' với {len(df_cashflow)} rows")
else:
    print(f"⚠️ File {cashflow_csv} không tìm thấy")

# Table 2: Anomaly Detection
if os.path.exists(anomaly_csv):
    df_anomaly = pd.read_csv(anomaly_csv)
    df_anomaly['txn_date'] = df_anomaly['txn_date'].apply(format_date)
    df_anomaly.to_sql('anomaly_result', conn, if_exists='replace', index=False)
    print(f"✅ Đã tạo table 'anomaly_result' với {len(df_anomaly)} rows")
else:
    print(f"⚠️ File {anomaly_csv} không tìm thấy")

conn.close()

print(f"\n✅ Hoàn thành! File '{db_file}' đã được tạo")
print(f"📁 Vị trí: {os.path.abspath(db_file)}")
