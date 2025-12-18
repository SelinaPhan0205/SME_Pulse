import pandas as pd
from datetime import datetime, timedelta

# Tạo dữ liệu từ 11/12/2025 đến 28/02/2026 (75 ngày)
start_date = datetime(2025, 12, 11)
end_date = datetime(2026, 2, 28)

# Generate dates
dates = []
current = start_date
while current <= end_date:
    dates.append(current)
    current += timedelta(days=1)

# Tạo forecast với:
# - Base: 42M (mid-range)
# - Trend: +100k per day (tăng dần từ từ)
# - Noise: -500k đến +500k random
# - Lower bound: -5% from yhat
# - Upper bound: +5% from yhat

import numpy as np
np.random.seed(42)

data = []
for idx, date in enumerate(dates):
    base = 42_000_000  # 42M
    trend = idx * 100_000  # +100k mỗi ngày
    noise = np.random.uniform(-500_000, 500_000)
    
    yhat = base + trend + noise
    yhat_lower = yhat * 0.95
    yhat_upper = yhat * 1.05
    
    # Format: chỉ giữ 2 chữ số thập phân
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
print("\n📊 Sample data:")
print(df.head(10))
