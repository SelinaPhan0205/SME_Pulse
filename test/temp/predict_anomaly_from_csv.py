import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.ensemble import IsolationForest
import os

# Đọc dữ liệu mock
mock_csv = '../mock_fact_bank_txn.csv'
df = pd.read_csv(mock_csv)

# Chọn các feature cần thiết cho model
features = ['amount_vnd', 'is_inflow', 'is_large_transaction']
X = df[features]

# Load model Isolation Forest đã train từ MLflow local
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///tmp/mlflow")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
model_uri = "models:/isolation_forest_anomaly_v1/1"  # Sửa version nếu cần

try:
    model = mlflow.sklearn.load_model(model_uri)
except Exception as e:
    print(f"Không load được model từ MLflow: {e}\nDùng IsolationForest mới train lại trên mock data...")
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(X)

# Dự đoán anomaly
anomaly_pred = model.predict(X)
df['anomaly'] = (anomaly_pred == -1).astype(int)
df[['txn_id', 'txn_date', 'amount_vnd', 'anomaly']].to_csv('anomaly_result.csv', index=False)
print('✅ Đã lưu kết quả phát hiện bất thường vào anomaly_result.csv')
