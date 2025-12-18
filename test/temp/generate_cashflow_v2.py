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

np.random.seed(42)

data = []
# Tạo trend từ 35M lên 125M trong 80 ngày
base_values = np.linspace(35_000_000, 125_000_000, len(dates))

for idx, date in enumerate(dates):
    # Trend tăng dần
    trend = base_values[idx]
    
    # Noise: +/- 20% để có biến động
    noise = np.random.uniform(-0.2, 0.2) * trend
    
    # Mỗi 10-15 ngày có 1 ngày đột ngột giảm (như bình thường)
    if idx > 0 and idx % 12 == 0:
        # Ngày này giảm xuống ~60% giá trị
        trend = trend * 0.6
        noise = np.random.uniform(-0.1, 0.1) * trend
    
    yhat = trend + noise
    yhat = max(35_000_000, min(125_000_000, yhat))  # Clamp trong range
    
    yhat_lower = yhat * 0.90  # -10%
    yhat_upper = yhat * 1.10  # +10%
    
    # Format: 2 chữ số thập phân
    yhat = round(yhat, 2)
    yhat_lower = round(yhat_lower, 2)
    yhat_upper = round(yhat_upper, 2)
    
    data.append({
        'ds': date.strftime('%Y-%m-%d'),
        'yhat': yhat,
        'yhat_lower': yhat_lower,
        'yhat_upper': yhat_upper
    })

df = pd.DataFrame(data)
df.to_csv('cashflow_forecast_result.csv', index=False)

print(f"✅ Tạo cashflow_forecast_result.csv với {len(df)} rows")
print(f"   Date range: {dates[0].date()} to {dates[-1].date()}")
print(f"   Range: {df['yhat'].min():,.0f} ₫ to {df['yhat'].max():,.0f} ₫")
print(f"   Min-Max spread: {df['yhat'].max() - df['yhat'].min():,.0f} ₫")

print("\n📊 Sample data (mỗi 10 hàng):")
print(df.iloc[::10][['ds', 'yhat', 'yhat_lower', 'yhat_upper']])

# Check for sudden drops
for i in range(1, len(df)):
    drop = ((df['yhat'].iloc[i-1] - df['yhat'].iloc[i]) / df['yhat'].iloc[i-1]) * 100
    if drop > 30:
        print(f"\n📉 Ngày {df['ds'].iloc[i]}: Giảm {drop:.0f}% từ {df['yhat'].iloc[i-1]:,.0f} xuống {df['yhat'].iloc[i]:,.0f}")
