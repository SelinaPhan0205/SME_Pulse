import pandas as pd
import numpy as np
import mlflow
import mlflow.prophet
from prophet import Prophet
import os

# Đọc dữ liệu mock
mock_csv = '../mock_ml_training_cashflow_fcst.csv'
df = pd.read_csv(mock_csv)

# Load model Prophet đã train từ MLflow local
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///tmp/mlflow")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
model_uri = "models:/prophet_cashflow_v1/1"  # Sửa version nếu cần

try:
    model = mlflow.prophet.load_model(model_uri)
except Exception as e:
    print(f"Không load được model từ MLflow: {e}\nDùng model Prophet mới train lại trên mock data...")
    model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
    model.add_country_holidays(country_name='VN')
    regressors = [
        'is_weekend', 'is_holiday_vn', 'is_beginning_of_month', 'is_end_of_month',
        'sin_month', 'cos_month', 'sin_day_of_week', 'cos_day_of_week',
        'macro_gdp_growth', 'macro_inflation'
    ]
    for reg in regressors:
        model.add_regressor(reg)
    model.fit(df)

# Dự báo 75 ngày tiếp theo
forecast_days = 75
future = df.tail(1).copy()
future_dates = pd.date_range(start=future['ds'].values[0], periods=forecast_days+1, freq='D')[1:]
future_rows = []
for d in future_dates:
    row = {
        'ds': d.strftime('%Y-%m-%d'),
        'is_weekend': int(d.weekday() >= 5),
        'is_holiday_vn': int(d.weekday() == 6),
        'is_beginning_of_month': int(d.day <= 3),
        'is_end_of_month': int(d.day >= 28),
        'sin_month': float(np.sin(d.month)),
        'cos_month': float(np.cos(d.month)),
        'sin_day_of_week': float(np.sin(d.weekday())),
        'cos_day_of_week': float(np.cos(d.weekday())),
        'macro_gdp_growth': round(float(df['macro_gdp_growth'].mean()), 2),
        'macro_inflation': round(float(df['macro_inflation'].mean()), 2)
    }
    future_rows.append(row)
future_df = pd.DataFrame(future_rows)

# Dự báo
forecast = model.predict(future_df)
forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_csv('cashflow_forecast_result.csv', index=False)
print(f'✅ Đã lưu kết quả dự báo cashflow {forecast_days} ngày vào cashflow_forecast_result.csv')
