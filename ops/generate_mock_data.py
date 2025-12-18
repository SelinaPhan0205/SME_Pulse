import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random


# 1. Mock data cho bảng ml_training_cashflow_fcst
num_days = 150  # 5 tháng
start_date = datetime.today() - timedelta(days=num_days)
dates = [start_date + timedelta(days=i) for i in range(num_days)]

cashflow_data = []
for d in dates:
    # Tạo biến động mạnh hơn: tăng/giảm theo tuần, cuối tháng, random event, dịp lễ
    base = 50000000
    week_factor = np.sin(d.weekday() / 7 * 2 * np.pi) * 9000000
    end_month_factor = 15000000 if d.day >= 28 else 0
    holiday_factor = 20000000 if d.month == 2 and d.day in [8, 9, 10, 11, 12, 13, 14] else 0  # Tết âm lịch giả lập
    event_factor = np.random.choice([0, 12000000, -12000000], p=[0.8, 0.1, 0.1])
    y = int(base + week_factor + end_month_factor + holiday_factor + event_factor + np.random.normal(0, 7000000))
    cashflow_data.append({
        'ds': d.strftime('%Y-%m-%d'),
        'y': max(y, 1000000),
        'is_weekend': int(d.weekday() >= 5),
        'is_holiday_vn': int(d.weekday() == 6 or (d.month == 2 and d.day in [8, 9, 10, 11, 12, 13, 14])),
        'is_beginning_of_month': int(d.day <= 3),
        'is_end_of_month': int(d.day >= 28),
        'sin_month': np.sin(d.month),
        'cos_month': np.cos(d.month),
        'sin_day_of_week': np.sin(d.weekday()),
        'cos_day_of_week': np.cos(d.weekday()),
        'macro_gdp_growth': round(np.random.uniform(5.5, 7.0), 2),
        'macro_inflation': round(np.random.uniform(2.5, 4.0), 2)
    })

cashflow_df = pd.DataFrame(cashflow_data)
cashflow_df.to_csv('mock_ml_training_cashflow_fcst.csv', index=False)

# 2. Mock data cho bảng fact_bank_txn
num_txn = 500
bank_txn_data = []
for i in range(num_txn):
    txn_date = start_date + timedelta(days=random.randint(0, num_days-1))
    amount = int(np.random.normal(20000000, 10000000))
    direction = random.choice(['in', 'out'])
    bank_txn_data.append({
        'txn_id': f'TXN{i+1:05d}',
        'txn_date': txn_date.strftime('%Y-%m-%d'),
        'amount_vnd': max(amount, 1000000),
        'direction_in_out': direction,
        'currency_code': 'VND',
        'counterparty_name': f'CP_{random.randint(1, 50)}',
        'is_inflow': int(direction == 'in'),
        'is_large_transaction': int(amount > 30000000),
        'transaction_category': random.choice(['receivable', 'payable', 'payroll', 'other']),
        'created_at': txn_date.strftime('%Y-%m-%d %H:%M:%S')
    })

bank_txn_df = pd.DataFrame(bank_txn_data)
bank_txn_df.to_csv('mock_fact_bank_txn.csv', index=False)

print('✅ Đã tạo xong mock data:')
print(' - mock_ml_training_cashflow_fcst.csv')
print(' - mock_fact_bank_txn.csv')
