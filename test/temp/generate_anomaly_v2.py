import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Tạo dữ liệu từ 11/12/2025 đến 28/02/2026 (80 ngày)
start_date = datetime(2025, 12, 11)
end_date = datetime(2026, 2, 28)

# Generate dates
dates = []
current = start_date
while current <= end_date:
    dates.append(current)
    current += timedelta(days=1)

# Chỉ có 8-10 giao dịch bất thường trong toàn bộ 80 ngày
np.random.seed(42)

data = []
txn_id = 1
anomaly_count = 0
max_anomalies = 9  # Chỉ 9 anomalies

for day_idx, date in enumerate(dates):
    # Mỗi ngày có 1-2 giao dịch bình thường
    num_txn = np.random.randint(1, 3)
    
    for txn_idx in range(num_txn):
        amount = np.random.uniform(15_000_000, 25_000_000)
        is_anomaly = 0
        
        # Random 9 ngày có anomaly (khoảng cách ~9 ngày)
        if anomaly_count < max_anomalies and day_idx % 9 == 0 and txn_idx == 0:
            amount = np.random.uniform(50_000_000, 75_000_000)
            is_anomaly = 1
            anomaly_count += 1
        
        # Format: 2 chữ số thập phân
        amount = round(amount, 2)
        
        data.append({
            'txn_id': f'TXN{str(txn_id).zfill(5)}',
            'txn_date': date.strftime('%Y-%m-%d'),
            'amount_vnd': amount,
            'anomaly': is_anomaly
        })
        txn_id += 1

df = pd.DataFrame(data)

# Lọc chỉ các anomalies để kiểm tra
anomalies = df[df['anomaly'] == 1]
print(f"✅ Tạo anomaly_result.csv với {len(df)} transactions")
print(f"   - Bình thường: {len(df[df['anomaly'] == 0])}")
print(f"   - Bất thường: {len(anomalies)}")
print(f"   Date range: {dates[0].date()} to {dates[-1].date()}")

df.to_csv('anomaly_result.csv', index=False)

print("\n📊 Anomalies:")
print(anomalies[['txn_id', 'txn_date', 'amount_vnd']])
