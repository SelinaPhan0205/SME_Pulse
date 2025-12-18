# 🔄 SQL Feature Store & ML Training Datasets

**Date**: January 2025  
**Status**: ✅ All features and training datasets converted to dbt SQL models  
**Location**: `dbt/models/silver/features/` + `dbt/models/silver/ml_training/`

---

## 📋 Overview

Tất cả **Python code** đã được chuyển đổi thành **dbt SQL models** chạy trực tiếp trên Trino. 

**Lợi ích**:
- ✅ Tối ưu hoá: Chạy SQL trực tiếp trên data warehouse (Trino) thay vì Python
- ✅ Scalability: Xử lý millions of rows hiệu quả hơn
- ✅ Maintenance: Dễ quản lý và version control trong dbt
- ✅ Materialization: Tự động cache kết quả (table/incremental)
- ✅ Testing: dbt built-in tests (not_null, unique, accepted_values)

---

## 🗂️ **Cấu trúc Thư Mục**

```
dbt/models/silver/
├── features/                          (Feature Store)
│   ├── ftr_daily_cashflow.sql        ✅ Daily cash flows
│   ├── ftr_transaction_anomaly.sql   ✅ Transaction z-scores
│   ├── ftr_invoice_risk.sql          ✅ Invoice risk metrics
│   ├── ftr_payment_pattern.sql       ✅ Customer payment patterns
│   ├── ftr_transaction_text.sql      ✅ Text features
│   ├── ftr_customer_behavior.sql     ✅ Customer aggregates
│   └── schema.yml                    📋 Documentation
│
└── ml_training/                       (ML Training Datasets)
    ├── ml_training_cashflow_fcst.sql     ✅ Prophet training (time series)
    ├── ml_training_anomaly_det.sql      ✅ Isolation Forest training
    ├── ml_training_ar_scoring.sql       ✅ XGBoost/LightGBM training
    └── ml_training_payment_pred.sql     ✅ Payment prediction training
```

---

## 🚀 **Cách Chạy**

### **Option 1: Chạy tất cả features**
```bash
cd /e/UIT/SME_Pulse
dbt run --models tag:features

# Hoặc chạy specific folder
dbt run --models path:dbt/models/silver/features
```

### **Option 2: Chạy tất cả ML training datasets**
```bash
dbt run --models tag:ml_training

# Hoặc chạy specific folder
dbt run --models path:dbt/models/silver/ml_training
```

### **Option 3: Chạy cái gì đó cụ thể**
```bash
# Chỉ chạy daily cashflow feature
dbt run --models ftr_daily_cashflow

# Chỉ chạy cashflow forecast training dataset
dbt run --models ml_training_cashflow_fcst

# Chạy một model và tất cả downstream
dbt run --models +ftr_daily_cashflow+
```

### **Option 4: Full pipeline (Features → Training)**
```bash
# Chạy toàn bộ silver layer (features + training)
dbt run --models path:dbt/models/silver

# Với testing
dbt run --models path:dbt/models/silver && dbt test
```

---

## 📊 **Data Dictionary**

### **Features (6 tables)**

| Model | Rows | Grain | Refresh | Purpose |
|---|---|---|---|---|
| `ftr_daily_cashflow` | ~730-800 | 1 row/day/flow_type | Daily | Prophet forecasting input |
| `ftr_transaction_anomaly` | ~50k-100k | 1 row/transaction | Daily | Isolation Forest training |
| `ftr_invoice_risk` | ~10k-50k | 1 row/invoice | Daily | AR priority scoring |
| `ftr_payment_pattern` | ~1k-10k | 1 row/customer | Daily | Customer segmentation |
| `ftr_transaction_text` | ~5k-20k | 1 row/transaction | Daily | Text categorization (RAG) |
| `ftr_customer_behavior` | ~1k-10k | 1 row/customer | Daily | Customer analysis |

### **ML Training Datasets (4 tables)**

| Model | Rows | Grain | Target | Model Type |
|---|---|---|---|---|
| `ml_training_cashflow_fcst` | ~730 | 1 row/day/flow | y (amount_vnd) | Prophet (Time Series) |
| `ml_training_anomaly_det` | ~50k | 1 row/txn | is_anomaly_label (0/1) | Isolation Forest |
| `ml_training_ar_scoring` | ~10k | 1 row/invoice | risk_label_encoded (0/1/2) | XGBoost/LightGBM |
| `ml_training_payment_pred` | ~1k | 1 row/customer | will_pay_on_time_label (0/1) | Logistic Regression |

---

## 🔄 **Data Flow Example**

### **Scenario 1: Daily Cashflow Forecasting**
```
Silver Layer:
stg_payments_vn ──────────────┐
                              ├──> ftr_daily_cashflow
stg_ar_invoices_vn ───────────┘     (aggregate by day)
                                          │
                                          ▼
                           ml_training_cashflow_fcst
                           (add features: lag, ma)
                                          │
                                          ▼
                           [Prophet Model]
                           (python: import parquet)
                                          │
                                          ▼
                           Gold Layer:
                           ml_score_cashflow_forecast
```

### **Scenario 2: Transaction Anomaly Detection**
```
Silver Layer:
stg_payments_vn ──────────> ftr_transaction_anomaly
                            (z-scores: rolling stats)
                                    │
                                    ▼
                            ml_training_anomaly_det
                            (add features: spikes, hours)
                                    │
                                    ▼
                            [Isolation Forest Model]
                            (python: import parquet)
                                    │
                                    ▼
                            Gold Layer:
                            ml_score_transaction_anomaly
```

---

## 💾 **Output Tables**

### **Tất cả output được lưu trong Trino**:
```sql
-- View feature tables
SELECT COUNT(*) FROM sme_lake.silver.ftr_daily_cashflow;
SELECT COUNT(*) FROM sme_lake.silver.ftr_transaction_anomaly;
SELECT COUNT(*) FROM sme_lake.silver.ftr_invoice_risk;
SELECT COUNT(*) FROM sme_lake.silver.ftr_payment_pattern;
SELECT COUNT(*) FROM sme_lake.silver.ftr_transaction_text;
SELECT COUNT(*) FROM sme_lake.silver.ftr_customer_behavior;

-- View training datasets
SELECT COUNT(*) FROM sme_lake.silver.ml_training_cashflow_fcst;
SELECT COUNT(*) FROM sme_lake.silver.ml_training_anomaly_det;
SELECT COUNT(*) FROM sme_lake.silver.ml_training_ar_scoring;
SELECT COUNT(*) FROM sme_lake.silver.ml_training_payment_pred;
```

### **Export để Python model**:
```python
import pandas as pd
from trino.dbapi import connect

conn = connect(
    host='trino',
    port=8080,
    http_scheme='http',
    catalog='sme_lake',
    schema='silver'
)

# Load feature table
df_features = pd.read_sql(
    "SELECT * FROM ftr_daily_cashflow LIMIT 1000",
    conn
)

# Load training dataset
df_train = pd.read_sql(
    "SELECT * FROM ml_training_cashflow_fcst",
    conn
)

# Train model
from prophet import Prophet
model = Prophet()
model.fit(df_train[['ds', 'y']])
forecast = model.make_future_dataframe(periods=30)
predictions = model.predict(forecast)
```

---

## 🧪 **Testing**

### **Chạy tests cho features**:
```bash
# Test tất cả models trong features folder
dbt test --models path:dbt/models/silver/features

# Test specific model
dbt test --models ftr_daily_cashflow

# Test specific column
dbt test --select ftr_invoice_risk.transaction_date
```

### **Test examples (từ schema.yml)**:
```yaml
- name: ftr_daily_cashflow
  columns:
    - name: transaction_date
      data_tests:
        - not_null                    # ✓ Kiểm tra không null
        - dbt_utils.not_null_where:   # ✓ Conditional not_null
            where: "flow_type = 'INFLOW'"
    
    - name: flow_type
      data_tests:
        - not_null
        - accepted_values:            # ✓ Chỉ INFLOW/OUTFLOW
            values: ['INFLOW', 'OUTFLOW']
    
    - name: tx_count
      data_tests:
        - not_null
        - assert_positive             # ✓ > 0
```

---

## 📈 **Performance Notes**

### **Partitioning**:
- `ftr_daily_cashflow`: Partitioned by `transaction_date` (day)
- `ftr_transaction_anomaly`: Partitioned by `transaction_date` (day)
- `ftr_transaction_text`: Partitioned by `payment_date` (day)

### **Materialization**:
- Features: `table` (full refresh daily)
- Training: `table` (full refresh daily)
- Can change to `incremental` for large tables

### **Typical run times** (estimate):
- `ftr_daily_cashflow`: ~5 seconds (aggregate)
- `ftr_transaction_anomaly`: ~30 seconds (rolling window)
- `ftr_invoice_risk`: ~20 seconds (join + calculations)
- `ml_training_cashflow_fcst`: ~10 seconds (add features)
- Full pipeline: ~2-3 minutes

---

## 🔧 **Customization**

### **Thay đổi date range**:
```sql
-- Trong ftr_daily_cashflow.sql, line 18:
WHERE payment_date >= DATE(CURRENT_DATE - INTERVAL '24' MONTH)
-- Thay thành:
WHERE payment_date >= DATE(CURRENT_DATE - INTERVAL '12' MONTH)  -- 12 months
```

### **Thay đổi z-score threshold**:
```sql
-- Trong ftr_transaction_anomaly.sql, line 76:
ABS(z_score_method) > 3 OR ABS(z_score_region) > 3 as is_suspected_anomaly
-- Thay thành:
ABS(z_score_method) > 2.5 OR ABS(z_score_region) > 2.5 as is_suspected_anomaly
```

### **Thay đổi risk thresholds**:
```sql
-- Trong ftr_invoice_risk.sql, line 110:
WHEN days_overdue > 90 THEN 'HIGH_RISK'
WHEN days_overdue > 30 THEN 'MEDIUM_RISK'
-- Thay thành custom values...
```

---

## 📋 **Deployment Checklist**

- [x] Convert Python → SQL
- [x] Create feature models (6 tables)
- [x] Create training datasets (4 tables)
- [x] Add schema.yml documentation
- [ ] **NEXT**: Run `dbt run` to generate all tables
- [ ] **NEXT**: Run `dbt test` to validate data quality
- [ ] **NEXT**: Update Airflow DAG to call `dbt run` instead of Python
- [ ] **NEXT**: Export parquet files to Python model training
- [ ] **NEXT**: Monitor in Metabase

---

## 🔗 **Integration with Airflow**

### **Option 1: Direct dbt invocation**
```python
# In airflow/dags/sme_pulse_daily_etl.py

from airflow.operators.bash import BashOperator

task_features = BashOperator(
    task_id='dbt_features',
    bash_command='cd /e/UIT/SME_Pulse && dbt run --models path:dbt/models/silver/features',
    dag=dag
)

task_training = BashOperator(
    task_id='dbt_training',
    bash_command='cd /e/UIT/SME_Pulse && dbt run --models path:dbt/models/silver/ml_training',
    dag=dag
)

# Execution order
sme_pulse_silver_etl >> task_features >> task_training >> ml_model_training
```

### **Option 2: Use dbt-airflow integration**
```python
from cosmos import DbtDag

dbt_dag = DbtDag(
    dag_id='dbt_silver_features',
    project_dir='/e/UIT/SME_Pulse/dbt',
    profile_name='sme_lake',
    select='path:dbt/models/silver'
)
```

---

## 📞 **Support**

### **Issues?**
1. Check `dbt debug` - Verify Trino connection
2. Check `dbt run --profiles-dir ~/.dbt --models ftr_daily_cashflow` with verbosity
3. Check dbt logs: `~/.dbt/logs/dbt.log`

### **Questions?**
- Review model SQL: `dbt/models/silver/features/*.sql`
- Check schema docs: `dbt/models/silver/features/schema.yml`
- Run lineage: `dbt docs generate && dbt docs serve`

---

**Status**: ✅ Ready for dbt run  
**Last Updated**: January 2025  
**Next Step**: Execute `dbt run --models path:dbt/models/silver`
