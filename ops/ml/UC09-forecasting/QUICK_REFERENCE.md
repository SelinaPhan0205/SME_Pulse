# Prophet Model - Quick Commands

## ✅ Test Connection
```bash
docker compose exec airflow-webserver python /opt/ops/ml/test_connection.py
```

## 🎓 Train Model (Manual)
```bash
docker compose exec airflow-webserver python /opt/ops/ml/train_cashflow_model.py
```

## 🔮 Run Prediction (Manual)
```bash
docker compose exec airflow-webserver python /opt/ops/ml/predict_cashflow.py
```

## 📊 Query Predictions
```bash
# View all predictions
docker compose exec trino trino --catalog sme_lake --schema gold --execute \
  "SELECT * FROM ml_cashflow_forecast ORDER BY forecast_date LIMIT 10"

# View latest prediction batch
docker compose exec trino trino --catalog sme_lake --schema gold --execute \
  "SELECT forecast_date, predicted_cashflow/1e12 as cashflow_trillion_vnd 
   FROM ml_cashflow_forecast 
   WHERE prediction_timestamp = (SELECT MAX(prediction_timestamp) FROM ml_cashflow_forecast)
   ORDER BY forecast_date"
```

## 🔍 Check DAGs Status
```bash
# List all DAGs
docker compose exec airflow-webserver airflow dags list | grep ml

# Trigger training manually
docker compose exec airflow-webserver airflow dags trigger sme_pulse_ml_train_cashflow

# Trigger prediction manually  
docker compose exec airflow-webserver airflow dags trigger sme_pulse_ml_predict_cashflow
```

## 📈 Model Performance
- **MAPE: 0.73%** (Cross-validation)
- **Training rows: 501 days**
- **Regressors: 10 features** (seasonality + macro)
- **Forecast horizon: 30 days**
