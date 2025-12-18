import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Tạo dữ liệu từ 17/11/2025 đến 17/12/2025 (31 ngày)
start_date = datetime(2025, 11, 17)
end_date = datetime(2025, 12, 17)

# Generate dates
dates = []
current = start_date
while current <= end_date:
    dates.append(current)
    current += timedelta(days=1)

np.random.seed(42)

data = []
txn_id = 1

# Chỉ có 5 anomalies trong 31 ngày:
# 4 cái tiền THẤP (low severity) - 40-50M
# 1 cái tiền CAO (high severity) - 80-100M

anomaly_dates = {
    3: 'low',     # ngày thứ 4
    8: 'low',     # ngày thứ 9
    15: 'high',   # ngày thứ 16
    22: 'low',    # ngày thứ 23
    28: 'low',    # ngày thứ 29
}

for day_idx, date in enumerate(dates):
    # Mỗi ngày có 1-2 giao dịch bình thường
    num_txn = np.random.randint(1, 3)
    
    for txn_idx in range(num_txn):
        is_anomaly = 0
        amount = np.random.uniform(15_000_000, 25_000_000)  # bình thường 15-25M
        
        # Kiểm tra nếu ngày này có anomaly
        if day_idx in anomaly_dates:
            severity_type = anomaly_dates[day_idx]
            if severity_type == 'high':
                # Tiền cao: 80-100M
                amount = np.random.uniform(80_000_000, 100_000_000)
                is_anomaly = 1
            elif severity_type == 'low':
                # Tiền thấp: 40-50M (lớn hơn bình thường nhưng ko phải cao)
                amount = np.random.uniform(40_000_000, 50_000_000)
                is_anomaly = 1
        
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
