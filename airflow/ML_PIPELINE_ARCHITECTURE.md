# SME Pulse - ML/AI Pipeline Architecture

## 📋 TỔNG QUAN

Hệ thống SME Pulse sử dụng kiến trúc **Separation of Concerns** với 4 DAGs độc lập:

| DAG | Schedule | Vai trò | Use Cases |
|-----|----------|---------|-----------|
| `sme_pulse_daily_etl` | Daily 2AM | ETL + UC05 SQL Scoring | Bronze→Silver→Gold + AR Heuristic |
| `sme_pulse_ml_predict` | Triggered | AI Inference | UC09 + UC10 Predictions |
| `sme_pulse_ml_training` | Weekly (Sun 1AM) | AI Training | UC09 + UC10 Model Retraining |
| `sme_pulse_external_data_sync` | Monthly (1st day) | Reference Data | Macro/Geographic Data |

---

## 🔄 WORKFLOW

```
┌─────────────────────────────────────────────────────────────┐
│  DAG 1: sme_pulse_daily_etl (Daily 2AM)                     │
├─────────────────────────────────────────────────────────────┤
│  1. Verify Infrastructure (MinIO + Trino)                    │
│  2. Validate Bronze Layer                                    │
│  3. dbt Silver: Staging transformations                      │
│  4. dbt Gold: Dimensions                                     │
│  5. dbt Gold: Facts                                          │
│  6. dbt Gold: Links (1% sample)                              │
│  7. dbt Gold: KPIs                                           │
│  8. dbt Gold: ML Scores (UC05 - AR Priority Heuristic)       │
│  9. Trigger → DAG 2 (Async)                                  │
│ 10. Generate Report                                          │
│ 11. Send Notification                                        │
└─────────────────────────────────────────────────────────────┘
                    ↓ Trigger (Async)
┌─────────────────────────────────────────────────────────────┐
│  DAG 2: sme_pulse_ml_predict (Triggered)                    │
├─────────────────────────────────────────────────────────────┤
│  1. UC09: Prophet Cashflow Forecasting (30 days)            │
│  2. UC10: Isolation Forest Anomaly Detection (7 days)       │
│  3. Refresh Metabase Cache                                  │
│  4. Invalidate Redis Cache                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  DAG 3: sme_pulse_ml_training (Weekly Sun 1AM)              │
├─────────────────────────────────────────────────────────────┤
│  1. Train UC09: Prophet Model (Parallel)                    │
│  2. Train UC10: Isolation Forest Model (Parallel)           │
│  3. Validate Models (MLflow + MinIO)                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  DAG 4: sme_pulse_external_data_sync (Monthly 1st)          │
├─────────────────────────────────────────────────────────────┤
│  1. Ingest World Bank Data (GDP, Inflation, Unemployment)   │
│  2. Ingest Vietnam Provinces/Districts                      │
│  3. dbt Silver: External staging                            │
│  4. dbt Gold: External dimensions                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 USE CASES IMPLEMENTATION

### UC05: AR Priority Scoring (Heuristic)
- **Type:** SQL-based Rule Engine
- **Location:** `dbt/models/gold/ml_scores/ml_ar_priority_scores.sql`
- **Execution:** Part of DAG 1 (daily ETL)
- **Output:** `sme_lake.gold.ml_ar_priority_scores` (30K rows)
- **Scoring:** Overdue (0-40) + Amount (0-30) + Risk (0-30) = Priority Score

### UC09: Cashflow Forecasting (Prophet)
- **Type:** Time Series ML Model
- **Training:** DAG 3 (weekly) → `/opt/ops/ml/UC09-forecasting/train_cashflow_model.py`
- **Prediction:** DAG 2 (daily trigger) → `/opt/ops/ml/UC09-forecasting/predict_cashflow.py`
- **Model Storage:** MLflow @ `file:///tmp/mlflow`
- **Output:** `sme_lake.gold.ml_cashflow_forecast` (30-day forecasts)
- **Metrics:** MAPE = 0.73%, RMSE = 24.1B VND

### UC10: Anomaly Detection (Isolation Forest)
- **Type:** Unsupervised ML Model
- **Training:** DAG 3 (weekly) → `/opt/ops/ml/UC10-anomoly_detection/ops-ML-anomaly_detection/train_isolation_forest.py`
- **Detection:** DAG 2 (daily trigger) → `/opt/ops/ml/UC10-anomoly_detection/ops-ML-anomaly_detection/detect_anomalies.py`
- **Model Storage:** MLflow @ `file:///tmp/mlflow`
- **Output:** `sme_lake.gold.ml_anomaly_alerts` (anomaly flags)
- **Metrics:** Silhouette = 0.41, Contamination = 5%

---

## 📂 FILE STRUCTURE

```
airflow/
├── dags/
│   ├── sme_pulse_daily_etl.py          # DAG 1 (Daily ETL)
│   ├── sme_pulse_ml_predict.py         # DAG 2 (AI Inference) [NEW]
│   ├── sme_pulse_ml_training.py        # DAG 3 (AI Training) [NEW]
│   └── sme_pulse_external_data_sync.py # DAG 4 (Monthly Sync)
│
dbt/
├── models/
│   ├── silver/
│   │   ├── features/                   # Feature engineering
│   │   └── ml_training/                # Training datasets
│   └── gold/
│       ├── ml_scores/
│       │   └── ml_ar_priority_scores.sql  # UC05 Heuristic
│       ├── facts/
│       ├── dims/
│       └── KPI/
│
ops/
└── ml/
    ├── UC09-forecasting/               # Prophet Cashflow
    │   ├── train_cashflow_model.py
    │   ├── predict_cashflow.py
    │   ├── show_training_result.py
    │   └── utils.py
    │
    └── UC10-anomoly_detection/         # Isolation Forest Anomaly
        └── ops-ML-anomaly_detection/
            ├── train_isolation_forest.py
            ├── detect_anomalies.py
            ├── show_training_results.py
            └── utils.py
```

---

## 🚀 DEPLOYMENT CHECKLIST

### 1. Prerequisites
- ✅ Airflow 2.9+ running
- ✅ dbt 1.10+ with Trino adapter
- ✅ MLflow local filesystem configured
- ✅ Python packages: `prophet`, `scikit-learn`, `trino`, `mlflow`

### 2. DAG Deployment
```bash
# Copy DAGs to Airflow
cp airflow/dags/sme_pulse_*.py /path/to/airflow/dags/

# Restart Airflow
docker compose restart airflow-webserver airflow-scheduler

# Enable DAGs in UI
# - sme_pulse_daily_etl → Schedule: 0 2 * * *
# - sme_pulse_ml_predict → Schedule: None (triggered)
# - sme_pulse_ml_training → Schedule: 0 1 * * 0
# - sme_pulse_external_data_sync → Schedule: 0 0 1 * *
```

### 3. Initial Training
```bash
# Train models manually first time
docker compose exec airflow-webserver python /opt/ops/ml/UC09-forecasting/train_cashflow_model.py
docker compose exec airflow-webserver python /opt/ops/ml/UC10-anomoly_detection/ops-ML-anomaly_detection/train_isolation_forest.py

# Verify models in MLflow
docker compose exec airflow-webserver python /opt/ops/ml/UC09-forecasting/show_training_result.py
docker compose exec airflow-webserver python /opt/ops/ml/UC10-anomoly_detection/ops-ML-anomaly_detection/show_training_results.py
```

### 4. Testing
```bash
# Test DAG 1 (ETL)
airflow dags test sme_pulse_daily_etl 2025-01-01

# Test DAG 2 (Predict) - manually trigger
airflow dags trigger sme_pulse_ml_predict

# Test DAG 3 (Training)
airflow dags test sme_pulse_ml_training 2025-01-01
```

---

## 🔍 MONITORING

### Key Metrics to Monitor

**DAG 1 (ETL):**
- Execution time: < 20 min
- dbt test pass rate: 100%
- Gold layer row counts: dims (9), facts (6), KPIs (4), ml_scores (1)

**DAG 2 (Predict):**
- UC09 forecast coverage: 30 days
- UC10 anomaly rate: 3-5%
- Cache refresh time: < 5 min

**DAG 3 (Training):**
- UC09 MAPE: < 1%
- UC10 Silhouette: > 0.3
- Model file size: < 100MB

### Alerts
- Email on failure (configured in `default_args`)
- Slack webhook (optional, add to `notification_helpers.py`)
- PagerDuty integration (for production)

---

## 🐛 TROUBLESHOOTING

### Common Issues

**1. DAG 2 not triggered after DAG 1**
```python
# Check TriggerDagRunOperator config
trigger_dag_id='sme_pulse_ml_predict'  # Must match exactly
wait_for_completion=False              # Async trigger
```

**2. ML scripts fail with "Module not found"**
```bash
# Add PYTHONPATH to Dockerfile
ENV PYTHONPATH="/opt:${PYTHONPATH}"
```

**3. MLflow connection timeout**
```python
# Verify MLflow URI in scripts
MLFLOW_TRACKING_URI = "file:///tmp/mlflow"  # Not http://localhost:5000
```

**4. dbt ml_scores model not found**
```bash
# Verify tag in dbt model
tags=['gold', 'ml_scores', 'uc05']

# Run manually
dbt run --select tag:ml_scores
```

---

## 📊 EXPECTED RESULTS

After full pipeline execution (DAG 1 → DAG 2):

| Table | Row Count | Update Frequency |
|-------|-----------|------------------|
| `ml_ar_priority_scores` | ~30,000 | Daily |
| `ml_cashflow_forecast` | 30 | Daily (30-day rolling) |
| `ml_anomaly_alerts` | ~1,000 | Daily (7-day window) |

---

## 🔄 MAINTENANCE

### Weekly Tasks
- Monitor DAG 3 training metrics
- Review anomaly detection false positives
- Validate forecast accuracy vs actuals

### Monthly Tasks
- Retrain models if MAPE > 2%
- Archive old predictions (> 90 days)
- Update macro data (DAG 4)

### Quarterly Tasks
- Feature engineering review
- Model hyperparameter tuning
- Performance optimization

---

## 📞 SUPPORT

- **Data Engineering Team:** data-eng@company.com
- **ML Engineering Team:** ml-eng@company.com
- **Documentation:** [Confluence Link]
- **Runbook:** [Internal Wiki]

---

**Last Updated:** 2025-11-13
**Version:** 1.0.0
**Maintained by:** Data Engineering Team
