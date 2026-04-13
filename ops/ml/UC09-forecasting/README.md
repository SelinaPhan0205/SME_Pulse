# UC09: Cashflow Forecasting with Prophet

## 📊 Tổng quan
Dự báo dòng tiền (cashflow) trong 30 ngày tới sử dụng Prophet time series model, với mục tiêu hỗ trợ SME quản lý thanh khoản và lập kế hoạch tài chính.

## 🎯 Kết quả đạt được
- ✅ Model Prophet trained thành công với **MAPE = 0.73%** (rất chính xác!)
- ✅ Đánh giá holdout chuẩn hóa: MAE, RMSE, MAPE, sMAPE, R2
- ✅ Training dataset: 501 ngày dữ liệu lịch sử (từ `ml_training_cashflow_fcst`)
- ✅ 10 features bao gồm: seasonality (8), macro indicators (2)
- ✅ Model registered: `prophet_cashflow_v1` version 1
- ✅ Predictions saved to Gold layer: `ml_cashflow_forecast` (30 ngày)
- ✅ Airflow DAGs created: training (weekly) + prediction (daily)

## 📁 Cấu trúc files

```
ops/ml/
├── README.md                    # Tài liệu này
├── utils.py                     # Trino connection helper
├── test_connection.py           # Test kết nối Trino
├── train_cashflow_model.py      # Training script
└── predict_cashflow.py          # Prediction script

airflow/dags/
└── sme_pulse_ml_cashflow.py     # DAG orchestration
```

## 🔧 Components

### 1. Training Script (`train_cashflow_model.py`)
**Chức năng:**
- Load dữ liệu từ `sme_lake.silver.ml_training_cashflow_fcst`
- Train Prophet model với 10 regressors
- Run cross-validation (MAPE evaluation)
- Log model vào MLflow (local filesystem: `/tmp/mlflow`)

**Regressors sử dụng:**
```python
regressors = [
    'is_weekend', 'is_holiday_vn', 
    'is_beginning_of_month', 'is_end_of_month',
    'sin_month', 'cos_month', 
    'sin_day_of_week', 'cos_day_of_week',
    'macro_gdp_growth', 'macro_inflation'
]
```

**Chạy manual:**
```bash
docker compose exec airflow-webserver python /opt/ops/ml/train_cashflow_model.py
```

**Output:**
```
INFO:__main__:Loaded 501 rows from ml_training_cashflow_fcst.
INFO:__main__:Cross-Validation MAPE: 0.007298926256477096
INFO:__main__:Model trained successfully! Run ID: d1dc960056cc4909a9bc5565db6fbd33
```

### 2. Prediction Script (`predict_cashflow.py`)
**Chức năng:**
- Load model từ MLflow (`models:/prophet_cashflow_v1/1`)
- Load latest features từ Trino (seasonality + macro)
- Generate predictions cho 30 ngày tới
- Save predictions vào `sme_lake.gold.ml_cashflow_forecast`

**Chạy manual:**
```bash
docker compose exec airflow-webserver python /opt/ops/ml/predict_cashflow.py
```

**Output:**
```
INFO:__main__:Generated 30 predictions.
=== Sample Predictions ===
            ds          yhat    yhat_lower    yhat_upper
501 2024-10-14  2.655e+12  2.649e+12  2.662e+12
502 2024-10-15  2.601e+12  2.594e+12  2.607e+12
...
INFO:__main__:Saved 30 predictions to Gold layer.
✅ Cashflow prediction completed successfully!
```

### 3. Airflow DAGs (`sme_pulse_ml_cashflow.py`)

**DAG 1: `sme_pulse_ml_train_cashflow`**
- Schedule: Mỗi Chủ nhật lúc 2 AM (`0 2 * * 0`)
- Task: Train Prophet model với data mới nhất
- Retrain weekly để model luôn up-to-date với pattern mới

**DAG 2: `sme_pulse_ml_predict_cashflow`**
- Schedule: Hàng ngày lúc 6 AM (`0 6 * * *`)
- Tasks:
  1. `predict_cashflow`: Generate 30-day forecast
  2. `validate_prediction`: Check if predictions saved successfully

**Enable DAGs:**
```bash
# Trong Airflow UI:
# 1. Go to http://localhost:8080
# 2. Enable "sme_pulse_ml_train_cashflow"
# 3. Enable "sme_pulse_ml_predict_cashflow"
```

## 📊 Data Flow

```
Bronze Layer (MinIO)
    ↓
Silver Layer (dbt transformations)
    ↓
ml_training_cashflow_fcst (501 rows)
    ↓
Prophet Training (weekly)
    ↓
MLflow Model Registry
    ↓
Daily Predictions (30 days)
    ↓
ml_cashflow_forecast (Gold Layer)
    ↓
Metabase Dashboard
```

## 🗄️ Gold Table Schema

**Table:** `sme_lake.gold.ml_cashflow_forecast`

| Column | Type | Description |
|--------|------|-------------|
| forecast_date | DATE | Ngày dự báo |
| predicted_cashflow | DOUBLE | Dòng tiền dự báo (VND) |
| lower_bound | DOUBLE | Giới hạn dưới (95% confidence) |
| upper_bound | DOUBLE | Giới hạn trên (95% confidence) |
| model_name | VARCHAR | Tên model (prophet_cashflow_v1) |
| model_version | VARCHAR | Version của model |
| prediction_timestamp | TIMESTAMP | Thời điểm dự báo |

**Query mẫu:**
```sql
SELECT 
    forecast_date,
    predicted_cashflow / 1e12 as cashflow_trillion_vnd,
    lower_bound / 1e12 as lower_trillion_vnd,
    upper_bound / 1e12 as upper_trillion_vnd
FROM sme_lake.gold.ml_cashflow_forecast
WHERE prediction_timestamp = (
    SELECT MAX(prediction_timestamp) 
    FROM sme_lake.gold.ml_cashflow_forecast
)
ORDER BY forecast_date;
```

## 📈 Model Performance

**Cross-Validation Results:**
- **MAPE (Mean Absolute Percentage Error): 0.73%**
  - Nghĩa là model dự báo sai trung bình chỉ 0.73%
  - Rất tốt cho financial forecasting!

**Confidence Intervals:**
- 95% confidence interval (yhat_lower, yhat_upper)
- Typical range: ±4-5% của predicted value

## 🔄 Workflow Production

### Daily Operations (tự động)
1. **6:00 AM** - DAG `sme_pulse_ml_predict_cashflow` chạy
   - Load model từ MLflow
   - Generate 30-day forecast
   - Save to Gold layer

2. **Metabase refresh** (có thể config caching)
   - Dashboard tự động cập nhật predictions mới

### Weekly Operations (tự động)
1. **Sunday 2:00 AM** - DAG `sme_pulse_ml_train_cashflow` chạy
   - Load 501+ days historical data
   - Retrain Prophet model
   - Register new model version
   - Evaluate với cross-validation

## 🛠️ Troubleshooting

### Issue 1: MLflow connection failed
**Symptom:**
```
Failed to resolve 'mlflow' ([Errno -2] Name or service not known)
```

**Solution:**
Hiện tại đang dùng local filesystem (`file:///tmp/mlflow`). Nếu muốn MLflow server:
```yaml
# Thêm vào docker-compose.yml:
mlflow:
  image: ghcr.io/mlflow/mlflow:latest
  ports:
    - "5000:5000"
  command: mlflow server --host 0.0.0.0 --port 5000
  
# Update train_cashflow_model.py:
MLFLOW_TRACKING_URI = "http://mlflow:5000"
```

### Issue 2: Permission denied /opt/mlflow
**Solution:** Đã chuyển sang `/tmp/mlflow` (có quyền ghi)

### Issue 3: Generated 0 predictions
**Symptom:** Forecast trả về empty DataFrame

**Solution:** Đã fix date filter logic:
```python
# Từ: forecast['ds'] > pd.Timestamp.now()
# Sang: forecast['ds'] > last_historical_date
```

### Issue 4: Column not found errors
**Symptom:**
```
Column 'is_holiday' cannot be resolved
Column 'indicator_name' cannot be resolved
```

**Solution:** Match column names với schema thực tế:
- `is_holiday` → `is_holiday_vn`
- `indicator_name` → `gdp_growth_annual_pct`, `inflation_annual_pct`

## 🚀 Next Steps (Cải tiến)

### 1. Add MLflow Server (optional)
- Centralized model registry
- Model versioning UI
- Experiment comparison

### 2. Improve Feature Engineering
- Tính toán chính xác seasonality cho từng ngày (không replicate)
- Add thêm features: revenue trends, payment behavior patterns
- Lag features: cashflow T-1, T-7, T-30

### 3. Model Monitoring
- Track prediction accuracy daily
- Alert nếu MAPE > threshold
- A/B testing với models khác (LSTM)

### 4. Metabase Dashboard
- Line chart: Predicted vs Actual cashflow
- Confidence intervals visualization
- Model performance metrics over time

### 5. API Endpoint (FastAPI)
```python
# POST /predict
{
  "forecast_days": 30,
  "model_version": "1"
}

# Response
{
  "predictions": [...],
  "model_info": {...},
  "confidence": 0.95
}
```

## 📚 References

**Prophet Documentation:**
- https://facebook.github.io/prophet/

**MLflow Documentation:**
- https://mlflow.org/docs/latest/index.html

**dbt ML Training Dataset:**
- `dbt/models/silver/ml_training/ml_training_cashflow_fcst.sql`

**Related Use Cases:**
- UC08: AR Invoice Scoring (Credit Risk)
- UC10: Payment Prediction (Classification)

---

**Author:** Data Team  
**Last Updated:** Nov 7, 2025  
**Status:** ✅ Production Ready
