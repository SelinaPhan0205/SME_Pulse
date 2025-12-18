import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Tạo dữ liệu từ 11/12/2025 đến 28/02/2026
start_date = datetime(2025, 12, 11)
end_date = datetime(2026, 2, 28)

# Generate dates
dates = []
current = start_date
while current <= end_date:
    dates.append(current)
    current += timedelta(days=1)

# Tạo ~500 anomalies (tương tự như cũ)
# Phân bố: 1-2 anomalies per day (tổng cộng ~520 trong 75 ngày)
np.random.seed(42)

data = []
txn_id = 1
for day_idx, date in enumerate(dates):
    # Mỗi ngày có 1-2 giao dịch bình thường
    num_txn = np.random.randint(1, 3)
    
    for txn_idx in range(num_txn):
        amount = np.random.uniform(15_000_000, 25_000_000)
        is_anomaly = 0
        
        # Mỗi 5-7 ngày có 1-2 giao dịch bất thường (lớn hơn 40M)
        if np.random.random() < 0.15:  # 15% chance per transaction
            amount = np.random.uniform(40_000_000, 55_000_000)
            is_anomaly = 1
        
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

print("\n📊 Sample anomalies:")
print(anomalies.head(10))
