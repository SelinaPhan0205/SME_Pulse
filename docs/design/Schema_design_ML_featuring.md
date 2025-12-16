# SME Pulse – ML-First Feature Store Architecture

> **Mục tiêu**: Xây dựng **Feature Store trong Silver** (training truth), **Gold** cho BI/Analytics serve, với **CI/CD ML pipeline** và **data quality guardrails**. Tích hợp **Kaggle Invoices Dataset** cho AR/Payment Prediction.

---

## ⚠️ VẤN ĐỀ CẬU GẶP & FIX

### **Sai lầm ban đầu** ❌
```
Gold Layer = Direct training data + Feature engineering
```
**Vấn đề:**
- Gold = business aggregations (daily_revenue, KPIs) → high-level, lossy
- ML cần raw/semi-processed data (rows không aggregate)
- Thay đổi business logic ở Gold → phá mô hình cũ
- BI và ML team cùng edit Gold → conflict

### **Best Practice** ✅
```
Silver = Feature Store (training truth, detailed)
Gold = Aggregates + Score serve (BI dashboards + model predictions)
ML Pipeline = Train từ Silver, score đưa vào Gold
```

**Lợi ích:**
- **Separation of concerns**: BI team không ảnh hưởng Data Science
- **Reproducibility**: Feature không bị thay đổi khi BI update KPI
- **Governance**: Feature engineering có version, audit trail
- **Latency**: BI query Gold (aggregate, fast), ML train từ Silver (detailed, fresh)

---

## 📐 KIẾN TRÚC MỚI

```
┌──────────────────────────────────────────────────────────────┐
│                   LAKEHOUSE – ML-FIRST                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  BRONZE (Immutable Raw)                                      │
│  ├─ sales_snapshot_raw                                       │
│  ├─ payments_raw                                             │
│  ├─ shipments_raw                                            │
│  ├─ bank_txn_raw                                             │
│  ├─ kaggle_invoices_train.csv    ← ⭐ NEW                    │
│  └─ kaggle_invoices_test.csv     ← ⭐ NEW                    │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  SILVER – FEATURE STORE (Training Truth)                     │
│  ├─ 📊 Base Staging Tables (cleaned, typed, Vietnamized)    │
│  │  ├─ stg_orders_vn                                         │
│  │  ├─ stg_payments_vn                                       │
│  │  ├─ stg_shipments_vn                                      │
│  │  ├─ stg_bank_txn_vn                                       │
│  │  └─ stg_ar_invoices_vn        ← ⭐ NEW (from Kaggle)      │
│  │                                                           │
│  ├─ 🔄 Feature Engineering Tables (for ML)                  │
│  │  ├─ ftr_customer_behavior     ← RFM, churn risk          │
│  │  ├─ ftr_invoice_risk          ← DSO, overdue rate        │
│  │  ├─ ftr_payment_pattern       ← avg days late, methods   │
│  │  ├─ ftr_seasonality           ← month, quarter effects   │
│  │  └─ ftr_macroeconomic         ← world bank rates          │
│  │                                                           │
│  └─ 🎯 ML Training Datasets (fact + features, no leakage)   │
│     ├─ ml_training_payment_pred  ← Labels + features        │
│     ├─ ml_training_ar_scoring    ← Invoice + payment label  │
│     └─ ml_training_cashflow_fcst ← Time series features     │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  GOLD – ANALYTICS & SERVE LAYER                              │
│  ├─ 📊 Conformed Dimensions                                  │
│  │  ├─ dim_date, dim_customer, dim_product, ...              │
│  │  └─ dim_ar_customer           ← ⭐ NEW (AR behavior)     │
│  │                                                           │
│  ├─ 📈 Fact Tables (for BI)                                  │
│  │  ├─ fact_orders               ← Daily snapshot           │
│  │  ├─ fact_payments                                        │
│  │  ├─ fact_shipments                                       │
│  │  ├─ fact_bank_txn                                        │
│  │  └─ fact_ar_invoices          ← ⭐ NEW (DSO, overdue)    │
│  │                                                           │
│  ├─ 🔗 Link Tables (reconciliation)                         │
│  │  ├─ link_order_payment                                   │
│  │  ├─ link_payment_bank                                    │
│  │  └─ link_order_shipment                                  │
│  │                                                           │
│  ├─ 📊 KPI Marts (for BI dashboards)                        │
│  │  ├─ kpi_daily_revenue         ← Safe aggregates         │
│  │  ├─ kpi_payment_success_rate                            │
│  │  ├─ kpi_ar_dso_analysis       ← ⭐ NEW                   │
│  │  └─ kpi_reconciliation_daily                            │
│  │                                                          │
│  └─ 🤖 ML Score Serve (model predictions)                   │
│     ├─ score_payment_pred        ← Pred payment date       │
│     ├─ score_ar_priority         ← Collection priority      │
│     ├─ score_churn_risk          ← Customer churn risk      │
│     └─ score_cashflow_fcst       ← Predicted cash-in        │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  🚀 ML PIPELINE (External Orchestration)                     │
│  ├─ Data Validation              ← Great Expectations       │
│  ├─ Feature Preparation          ← SQL → Python DF          │
│  ├─ Model Training               ← Prophet, SKLearn, XGBoost│
│  ├─ Model Evaluation             ← Cross-validation         │
│  ├─ Model Versioning             ← MLflow, DVC              │
│  └─ Score Writing Back           ← Score → Gold tables      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 🎯 LAYER RESPONSIBILITIES

### **Silver = Feature Store (Training Truth)**

**Tính chất:**
- **Versioned**: Mỗi thay đổi feature → tạo version mới
- **Detailed**: Row-level data, không aggregate
- **Curated**: Đã clean, type-cast, handle missing
- **Lineage**: Track feature từ Bronze source
- **Searchable**: Feature metadata catalog

**Ai sử dụng:**
- Data Scientists (train models)
- ML Engineers (feature development)
- Data Analysts (exploratory analysis)

**SLA:**
- Data freshness: Real-time → Hourly
- Availability: 99%
- Retention: 2-3 years (for retraining)

### **Gold = Analytics & Serve (BI + Model Output)**

**Tính chất:**
- **Aggregated**: Pre-calculated KPIs, business metrics
- **Denormalized**: Star schema, optimized for queries
- **Served**: Model scores, predictions
- **Governed**: Row-level security, masking
- **Fast**: Optimized for BI tools (Metabase, Power BI)

**Ai sử dụng:**
- Business Analysts (dashboards)
- Executives (KPI reports)
- Applications (model scores API)

**SLA:**
- Query latency: < 5 seconds
- Availability: 99.9%
- Retention: 1-2 years (compliance)

---

## 📋 SILVER LAYER DESIGN

### **1. Base Staging Tables** (Cleaned & Vietnamized)

Already exist, ví dụ:
- `stg_orders_vn` ← Orders with revenue, cost
- `stg_payments_vn` ← Payments with status, amount_vnd
- `stg_ar_invoices_vn` ← NEW: AR invoices from Kaggle

### **2. Feature Engineering Tables** (Calculated, NOT Aggregated)

These are **at row-level or slowly-changing dimensions**, designed for ML feature engineering.

#### **silver/features/ftr_customer_behavior.sql**
```sql
-- Customer-level features (slowly changing)
-- 1 row per customer = stable reference
{{ config(
    materialized='incremental',
    unique_key='customer_code',
    on_schema_change='append_new_columns',
    tags=['feature_store', 'customer_features']
) }}

with orders as (
    select 
        customer_code,
        count(*) as total_orders_ltm,
        sum(qty) as total_qty_ltm,
        sum(revenue) as total_revenue_ltm,
        avg(revenue) as avg_order_value,
        max(order_date) as last_order_date,
        min(order_date) as first_order_date,
        datediff('day', min(order_date), max(order_date)) as customer_age_days
    from {{ ref('stg_orders_vn') }}
    where order_date >= dateadd('month', -12, current_date)
    group by 1
),
payments as (
    select 
        customer_code,
        count(*) as total_payments_ltm,
        sum(amount_vnd) as total_paid_ltm,
        sum(case when status_std = 'paid' then 1 else 0 end) as paid_count,
        sum(case when status_std = 'pending' then 1 else 0 end) as pending_count
    from {{ ref('stg_payments_vn') }}
    where payment_date >= dateadd('month', -12, current_date)
    group by 1
),
combined as (
    select
        o.customer_code,
        o.total_orders_ltm,
        o.total_qty_ltm,
        o.total_revenue_ltm,
        o.avg_order_value,
        o.last_order_date,
        o.customer_age_days,
        
        -- RFM Features
        datediff('day', o.last_order_date, current_date) as recency_days,
        o.total_orders_ltm as frequency,
        o.total_revenue_ltm as monetary,
        
        -- Payment Features
        coalesce(p.total_payments_ltm, 0) as total_payments_ltm,
        coalesce(p.paid_count, 0) as paid_count,
        coalesce(p.pending_count, 0) as pending_count,
        case 
            when o.total_orders_ltm > 0 
            then round(1.0 * coalesce(p.paid_count, 0) / o.total_orders_ltm, 3)
            else 0 
        end as payment_completion_rate,
        
        -- Segment
        case
            when o.total_revenue_ltm > 1000000000 and datediff('day', o.last_order_date, current_date) <= 30 then 'VIP'
            when o.total_orders_ltm >= 10 and datediff('day', o.last_order_date, current_date) <= 30 then 'Active'
            when datediff('day', o.last_order_date, current_date) > 90 then 'Inactive'
            else 'At Risk'
        end as customer_segment,
        
        current_timestamp as ftr_updated_at
    from orders o
    left join payments p on o.customer_code = p.customer_code
)
select * from combined;
```

#### **silver/features/ftr_invoice_risk.sql**
```sql
-- Invoice-level risk features (row per invoice)
{{ config(
    materialized='incremental',
    unique_key='invoice_id',
    on_schema_change='append_new_columns',
    tags=['feature_store', 'ar_features']
) }}

with invoices as (
    select
        invoice_id,
        customer_number,
        business_code,
        invoice_date,
        baseline_create_date,
        due_date,
        payment_date,
        invoice_amount,
        isOpen,
        isLate,
        
        -- Days Overdue calculation
        case
            when isOpen = true then datediff('day', due_date, current_date)
            when payment_date is not null then datediff('day', due_date, payment_date)
            else 0
        end as days_overdue,
        
        -- Days to Pay
        case
            when payment_date is not null then datediff('day', invoice_date, payment_date)
            else null
        end as days_to_pay,
        
        -- Invoice aging
        datediff('day', due_date, current_date) as aging_days
    from {{ ref('stg_ar_invoices_vn') }}
),
risk_features as (
    select
        invoice_id,
        customer_number,
        business_code,
        invoice_amount,
        invoice_date,
        due_date,
        payment_date,
        days_overdue,
        days_to_pay,
        aging_days,
        
        -- Risk flags
        case when days_overdue > 30 then 1 else 0 end as is_overdue_30,
        case when days_overdue > 60 then 1 else 0 end as is_overdue_60,
        case when isOpen = true and aging_days > 90 then 1 else 0 end as is_high_risk,
        
        -- Invoice size bracket
        case
            when invoice_amount < 10000000 then 'small'
            when invoice_amount < 100000000 then 'medium'
            else 'large'
        end as invoice_size_bracket,
        
        current_timestamp as ftr_updated_at
    from invoices
)
select * from risk_features;
```

#### **silver/features/ftr_payment_pattern.sql**
```sql
-- Customer payment pattern features (slowly changing)
{{ config(
    materialized='incremental',
    unique_key='customer_code',
    on_schema_change='append_new_columns',
    tags=['feature_store', 'payment_features']
) }}

with payment_history as (
    select
        customer_code,
        method_code,
        payment_date,
        amount_vnd,
        status_std,
        datediff('day', payment_date, lag(payment_date) over (partition by customer_code order by payment_date)) as days_between_payments
    from {{ ref('stg_payments_vn') }}
    where payment_date >= dateadd('month', -12, current_date)
),
aggregated as (
    select
        customer_code,
        
        -- Payment method preference
        mode(method_code) as preferred_payment_method,
        
        -- Payment timing
        avg(days_between_payments) as avg_days_between_payments,
        stddev(days_between_payments) as stddev_days_between_payments,
        
        -- Payment reliability
        round(sum(case when status_std = 'paid' then 1 else 0 end) * 1.0 / count(*), 3) as payment_success_rate,
        
        current_timestamp as ftr_updated_at
    from payment_history
    group by customer_code
)
select * from aggregated;
```

### **3. ML Training Datasets** (Fact + Features, No Data Leakage)

#### **silver/ml_training/ml_training_payment_pred.sql**
```sql
-- Training dataset for payment date prediction model
-- Features: invoice + customer behavior
-- Label: days_to_pay
-- Constraint: Use historical invoices only (no future data leak)

{{ config(
    materialized='table',
    tags=['feature_store', 'ml_training', 'payment_prediction']
) }}

with invoices as (
    select
        invoice_id,
        customer_number,
        invoice_amount,
        invoice_date,
        due_date,
        payment_date,
        baseline_create_date,
        business_code,
        
        -- Label: Days to pay (only for paid invoices)
        datediff('day', invoice_date, payment_date) as days_to_pay
    from {{ ref('ftr_invoice_risk') }}
    where payment_date is not null  -- Only completed invoices
      and invoice_date >= dateadd('year', -2, current_date)  -- 2 years history
      and days_to_pay >= 0  -- No negative days
      and days_to_pay <= 180  -- Remove outliers
),
customer_feats as (
    select 
        customer_code,
        payment_completion_rate,
        customer_age_days,
        recency_days,
        frequency,
        monetary
    from {{ ref('ftr_customer_behavior') }}
),
payment_patterns as (
    select
        customer_code,
        preferred_payment_method,
        avg_days_between_payments,
        payment_success_rate
    from {{ ref('ftr_payment_pattern') }}
),
combined as (
    select
        i.invoice_id,
        i.customer_number,
        i.invoice_amount,
        i.invoice_date,
        i.due_date,
        i.business_code,
        i.days_to_pay as target_days_to_pay,
        
        -- Customer features
        cf.payment_completion_rate,
        cf.customer_age_days,
        cf.recency_days,
        cf.frequency,
        cf.monetary,
        
        -- Payment pattern features
        coalesce(pp.preferred_payment_method, 'unknown') as preferred_payment_method,
        coalesce(pp.avg_days_between_payments, 0) as avg_days_between_payments,
        coalesce(pp.payment_success_rate, 0) as payment_success_rate,
        
        -- Time features
        month(i.invoice_date) as invoice_month,
        quarter(i.invoice_date) as invoice_quarter,
        dayofweek(i.invoice_date) as invoice_dayofweek,
        
        current_timestamp as training_prepared_at
    from invoices i
    left join customer_feats cf on i.customer_number = cf.customer_code
    left join payment_patterns pp on i.customer_number = pp.customer_code
)
select * from combined;
```

---

## 📊 GOLD LAYER DESIGN

### **New Dimensions for AR**

#### **gold/dims/dim_ar_customer.sql** (SCD Type 2)
```sql
-- AR Customer dimension with history
{{ config(
    materialized='incremental',
    unique_key=['customer_code', 'effective_from'],
    tags=['dimensions', 'ar_dimensions']
) }}

with customer_feats as (
    select
        customer_code,
        payment_completion_rate,
        customer_segment,
        ftr_updated_at
    from {{ ref('ftr_customer_behavior') }}
),
scd_logic as (
    select
        customer_code,
        payment_completion_rate,
        customer_segment,
        ftr_updated_at as effective_from,
        dateadd('day', -1, lead(ftr_updated_at) over (partition by customer_code order by ftr_updated_at)) as effective_to,
        case when lead(ftr_updated_at) over (partition by customer_code order by ftr_updated_at) is null 
             then true else false end as is_current
    from customer_feats
)
select 
    {{ dbt_utils.surrogate_key(['customer_code', 'effective_from']) }} as ar_customer_key,
    customer_code,
    payment_completion_rate,
    customer_segment,
    effective_from,
    effective_to,
    is_current
from scd_logic;
```

### **Fact Tables for AR**

#### **gold/facts/fact_ar_invoices.sql** (DSO Analysis)
```sql
-- AR invoice facts for DSO, overdue analysis
{{ config(
    materialized='incremental',
    unique_key='invoice_key',
    tags=['facts', 'ar_facts']
) }}

with invoices as (
    select
        ir.invoice_id,
        cast(to_char(ir.invoice_date, 'YYYYMMDD') as bigint) as date_key_invoice,
        cast(to_char(ir.due_date, 'YYYYMMDD') as bigint) as date_key_due,
        ir.customer_number as customer_key,
        ir.business_code,
        ir.invoice_amount,
        ir.days_overdue,
        ir.is_overdue_30,
        ir.is_overdue_60,
        ir.is_high_risk,
        ir.invoice_size_bracket,
        case when ir.payment_date is not null then 'paid' else 'open' end as status
    from {{ ref('ftr_invoice_risk') }} ir
)
select
    {{ dbt_utils.surrogate_key(['invoice_id', 'date_key_invoice']) }} as invoice_key,
    invoice_id,
    date_key_invoice,
    date_key_due,
    customer_key,
    business_code,
    invoice_amount,
    days_overdue,
    is_overdue_30,
    is_overdue_60,
    is_high_risk,
    invoice_size_bracket,
    status
from invoices;
```

### **KPI Marts for BI**

#### **gold/kpi/kpi_ar_dso_analysis.sql**
```sql
-- Days Sales Outstanding (DSO) and AR analytics
{{ config(
    materialized='incremental',
    unique_key='date_key',
    tags=['kpi', 'ar_kpi']
) }}

with daily_metrics as (
    select
        date_key_invoice as date_key,
        count(distinct invoice_id) as total_invoices,
        sum(invoice_amount) as total_invoice_amount,
        sum(case when status = 'paid' then invoice_amount else 0 end) as paid_amount,
        sum(case when status = 'open' then invoice_amount else 0 end) as open_amount,
        
        -- Overdue metrics
        sum(is_overdue_30) as invoices_overdue_30,
        sum(is_overdue_60) as invoices_overdue_60,
        sum(is_high_risk) as high_risk_invoices,
        
        -- DSO calculation (simplified)
        round(avg(days_overdue), 2) as avg_days_overdue,
        
        current_timestamp as kpi_updated_at
    from {{ ref('fact_ar_invoices') }}
    group by date_key_invoice
)
select * from daily_metrics;
```

### **ML Score Serve Tables**

#### **gold/ml_scores/score_payment_pred.sql**
```sql
-- Model predictions: predicted payment date
-- Updated by ML pipeline after model inference
{{ config(
    materialized='incremental',
    unique_key='invoice_id',
    tags=['ml_scores', 'payment_prediction']
) }}

select
    invoice_id,
    customer_number,
    predicted_days_to_pay,
    predicted_payment_date,
    model_version,
    prediction_confidence,
    prediction_timestamp,
    current_timestamp as score_inserted_at
from {{ source('ml_pipeline', 'payment_pred_scores') }}
where prediction_timestamp >= dateadd('day', -7, current_date);
```

---

## 🔄 ML PIPELINE ORCHESTRATION

### **Architecture: Airflow → Python → MLflow → dbt**

```
┌─────────────────────────────────────┐
│   Airflow DAG: ml_training_daily    │
├─────────────────────────────────────┤
│                                     │
│ 1. data_quality_check               │
│    └─ Great Expectations on Silver  │
│                                     │
│ 2. feature_preparation              │
│    └─ SQL query Silver features     │
│    └─ Load to Pandas                │
│                                     │
│ 3. model_training                   │
│    └─ Train Prophet/XGBoost/LGBM    │
│    └─ MLflow tracking               │
│                                     │
│ 4. model_evaluation                 │
│    └─ Cross-validation metrics      │
│    └─ Artifact logging              │
│                                     │
│ 5. batch_inference                  │
│    └─ Inference on recent data      │
│    └─ Write scores to temp table    │
│                                     │
│ 6. dbt_load_scores                  │
│    └─ dbt run --select gold.ml_scores
│    └─ Tests on score data           │
│                                     │
└─────────────────────────────────────┘
```

### **dbt Tags for Orchestration**

Thêm `dbt_project.yml`:
```yaml
models:
  sme_pulse:
    silver:
      +tags: ['silver', 'feature_store']
      features:
        +tags: ['silver', 'feature_store', 'ml_features']
      ml_training:
        +tags: ['silver', 'feature_store', 'ml_training_dataset']
    
    gold:
      +tags: ['gold', 'analytics']
      ml_scores:
        +tags: ['gold', 'ml_scores', 'production']
        +meta:
          owner: ml_platform
          sla: critical
```

---

## 🛡️ DATA QUALITY GUARDRAILS

### **1. Great Expectations for Silver Features**

File: `dbt/tests/ge/feature_quality.py`
```python
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest

def validate_features_before_training():
    context = gx.get_context()
    
    # Check stg_ar_invoices_vn
    batch_request = RuntimeBatchRequest(
        datasource_name="trino",
        data_connector_name="default",
        data_asset_name="silver.stg_ar_invoices_vn"
    )
    
    suite = context.suites.add(gx.ExpectationSuite(name="invoice_quality"))
    validator = context.get_validator(batch_request=batch_request, expectation_suite=suite)
    
    # Expectations
    validator.expect_column_to_exist("invoice_id")
    validator.expect_column_values_to_not_be_null("invoice_amount")
    validator.expect_column_values_to_be_between("invoice_amount", min_value=0)
    validator.expect_column_values_to_not_have_trailing_whitespace("customer_number")
    
    # Stat expectations (distribution shift detection)
    validator.expect_column_mean_to_be_between("invoice_amount", min_value=15000000, max_value=25000000)
    validator.expect_column_kl_divergence_from_list_to_be_less_than(
        "business_code", 
        partition_column="business_code",
        threshold=0.2  # KL divergence limit
    )
    
    checkpoint = validator.save_expectation_suite(discard_failed_expectations=False)
    results = context.run_checkpoint(checkpoint_name=suite.name)
    
    return results.success
```

### **2. dbt Tests for Features**

File: `dbt/tests/custom_tests.sql`
```sql
-- tests/feature_store_quality.sql
-- Ensure features don't have sudden changes

select
    ftr_customer_behavior.customer_code,
    ftr_customer_behavior.payment_completion_rate,
    lag(ftr_customer_behavior.payment_completion_rate, 1) over (
        partition by ftr_customer_behavior.customer_code 
        order by ftr_customer_behavior.ftr_updated_at
    ) as prev_rate
from {{ ref('ftr_customer_behavior') }}
where abs(
    ftr_customer_behavior.payment_completion_rate - 
    lag(ftr_customer_behavior.payment_completion_rate, 1) over (
        partition by ftr_customer_behavior.customer_code 
        order by ftr_customer_behavior.ftr_updated_at
    )
) > 0.3  -- Flag > 30% change in completion rate
having prev_rate is not null
```

### **3. Airflow Pipeline Guardrails**

File: `airflow/dags/ml_training_pipeline.py`
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import pandas as pd
from trino.dbapi import connect

default_args = {
    'owner': 'ml_platform',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': True,
    'email': ['ml_team@sme-pulse.vn']
}

dag = DAG(
    'ml_training_daily',
    default_args=default_args,
    schedule_interval='0 2 * * *',  # 2 AM every day
    tags=['ml', 'production']
)

def data_quality_check():
    """
    Pre-training guardrails:
    - Check null %
    - Check distribution shift (KL divergence)
    - Check data freshness
    """
    conn = connect(host='trino', port=8080, database='iceberg', schema='silver')
    
    # 1. Null check
    query_null = """
    SELECT 
        COUNT(*) as total_rows,
        SUM(CASE WHEN invoice_id IS NULL THEN 1 ELSE 0 END) as null_invoice_id,
        SUM(CASE WHEN invoice_amount IS NULL THEN 1 ELSE 0 END) as null_amount
    FROM stg_ar_invoices_vn
    WHERE invoice_date >= DATE(CURRENT_DATE - INTERVAL 7 DAY)
    """
    df_null = pd.read_sql(query_null, conn)
    null_rate = df_null['null_invoice_id'].values[0] / df_null['total_rows'].values[0]
    
    if null_rate > 0.05:  # > 5% nulls = fail
        raise ValueError(f"Too many nulls in invoice_id: {null_rate*100:.2f}%")
    
    # 2. Freshness check
    query_fresh = "SELECT MAX(invoice_date) as max_date FROM stg_ar_invoices_vn"
    df_fresh = pd.read_sql(query_fresh, conn)
    max_date = pd.to_datetime(df_fresh['max_date'].values[0])
    
    if (datetime.now() - max_date).days > 2:  # Data > 2 days old = warning
        raise ValueError(f"Data is stale: {max_date}")
    
    print(f"✅ Data quality check passed: {null_rate*100:.2f}% nulls, freshness OK")

def feature_preparation():
    """Load features from Silver, prepare for training"""
    # Query features from Silver
    # Save to training CSV for model pipeline
    pass

def model_training_with_tracking():
    """Train model with MLflow tracking"""
    import mlflow
    from prophet import Prophet
    import numpy as np
    
    mlflow.set_experiment("payment_prediction")
    
    with mlflow.start_run():
        # Prepare data
        df_train = pd.read_csv('/tmp/training_data.csv')
        
        # Log parameters
        mlflow.log_param("model_type", "Prophet")
        mlflow.log_param("training_rows", len(df_train))
        
        # Train
        model = Prophet(yearly_seasonality=True, weekly_seasonality=True)
        model.fit(df_train[['ds', 'y']])  # ds = date, y = target
        
        # Evaluate
        metrics = cross_validate(model, df_train, horizon=7, period=30, parallel="processes")
        mape = np.mean(metrics['mape'])
        
        mlflow.log_metric("MAPE", mape)
        mlflow.log_artifact(model, "prophet_model")
        
        print(f"✅ Model trained with MAPE: {mape:.4f}")

def batch_inference():
    """Generate predictions for all active invoices"""
    # Load trained model from MLflow
    # Inference on Silver features
    # Write scores to temp table
    pass

task_check = PythonOperator(
    task_id='data_quality_check',
    python_callable=data_quality_check,
    dag=dag
)

task_prep = PythonOperator(
    task_id='feature_preparation',
    python_callable=feature_preparation,
    dag=dag
)

task_train = PythonOperator(
    task_id='model_training',
    python_callable=model_training_with_tracking,
    dag=dag
)

task_infer = PythonOperator(
    task_id='batch_inference',
    python_callable=batch_inference,
    dag=dag
)

task_dbt = BashOperator(
    task_id='dbt_load_scores',
    bash_command='cd /opt/dbt && dbt run --select gold.ml_scores --threads 4',
    dag=dag
)

task_check >> task_prep >> task_train >> task_infer >> task_dbt
```

---

## 📥 KAGGLE INVOICES INTEGRATION

### **Step 1: Download & Ingest**

#### **airflow/dags/ingest_kaggle_invoices.py**
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import subprocess
import os
from minio import Minio

dag = DAG(
    'ingest_kaggle_invoices',
    schedule_interval='@monthly',  # Once per month
    tags=['bronze', 'kaggle', 'ar']
)

def download_kaggle_dataset():
    """
    Download Kaggle dataset
    Prerequisites:
    - Kaggle API key installed: ~/.kaggle/kaggle.json
    - In Dockerfile: pip install kaggle
    """
    dataset = "pradumn203/payment-date-prediction-for-invoices-dataset"
    output_path = "/tmp/kaggle_invoices"
    
    os.makedirs(output_path, exist_ok=True)
    
    # Download
    subprocess.run([
        "kaggle", "datasets", "download", 
        "-d", dataset, 
        "-p", output_path,
        "--unzip"
    ], check=True)
    
    print(f"✅ Downloaded to {output_path}")
    return output_path

def upload_to_minio(output_path):
    """Upload to MinIO bronze layer"""
    client = Minio(
        "minio:9000",
        access_key="minioadmin",
        secret_key="minioadmin123",
        secure=False
    )
    
    ingest_date = datetime.now().strftime("%Y%m%d")
    bucket = "sme-lake"
    
    for csv_file in ['train.csv', 'test.csv']:
        file_path = f"{output_path}/{csv_file}"
        object_name = f"bronze/raw/kaggle_invoices/{ingest_date}/{csv_file}"
        
        client.fput_object(bucket, object_name, file_path)
        print(f"✅ Uploaded {object_name}")

task_download = PythonOperator(
    task_id='download_kaggle',
    python_callable=download_kaggle_dataset,
    dag=dag
)

task_upload = PythonOperator(
    task_id='upload_to_minio',
    python_callable=upload_to_minio,
    dag=dag
)

task_download >> task_upload
```

### **Step 2: Bronze → Silver Transformation**

#### **models/silver/stg_ar_invoices_vn.sql**
```sql
-- AR invoices from Kaggle dataset
-- Mapping Kaggle columns → SME Pulse standard

{{ config(
    materialized='incremental',
    unique_key='invoice_id',
    on_schema_change='sync_all_columns',
    tags=['silver', 'ar_invoices', 'kaggle']
) }}

with src as (
    select * from {{ source('bronze', 'kaggle_invoices_raw') }}
),
normalized as (
    select
        -- Unique identifiers
        {{ dbt_utils.surrogate_key(['invoice_id']) }} as invoice_id_nat,
        invoice_id,
        customer_number,
        business_code,
        
        -- Dates (Kaggle → Standard format)
        try_to_date(invoice_date, 'DD-MMM-YYYY') as invoice_date,
        try_to_date(baseline_create_date, 'DD-MMM-YYYY') as baseline_create_date,
        try_to_date(due_in_date, 'DD-MMM-YYYY') as due_date,
        try_to_date(clear_date, 'DD-MMM-YYYY') as payment_date,
        
        -- Amount fields
        try_cast(total_open_amount as decimal(18,2)) as invoice_amount,
        
        -- Status flags
        case 
            when isOpen = 1 then true
            when isOpen = 0 then false
            else null 
        end as isOpen,
        case
            when isLate = 1 then true
            when isLate = 0 then false
            else null
        end as isLate,
        
        -- Additional features from Kaggle
        supply_days,
        credit_limit,
        business_year,
        
        current_timestamp as ingested_at
    from src
    where invoice_date >= dateadd('year', -3, current_date)  -- 3 years history
)
select * from normalized
{% if is_incremental() %}
  where ingested_at > (select max(ingested_at) from {{ this }})
{% endif %}
```

### **Step 3: Bronze Source Declaration**

#### **models/bronze.yml** (add)
```yaml
sources:
  - name: bronze
    schema: bronze
    tables:
      # ... existing tables ...
      - name: kaggle_invoices_raw
        description: "Kaggle Invoices Dataset - Payment Date Prediction"
        columns:
          - name: invoice_id
            description: Unique invoice identifier
          - name: customer_number
            tests:
              - not_null
          - name: invoice_date
          - name: due_in_date
          - name: clear_date
          - name: total_open_amount
            tests:
              - not_null
```

---

## 📋 CI/CD ML WORKFLOW

### **Git Strategy: Feature Branches for Models**

```bash
# Data Scientist creates feature branch
git checkout -b feature/ml-payment-prediction

# 1. Modify Silver features
# - Edit silver/features/ftr_invoice_risk.sql
# - dbt run --select silver.features

# 2. Create training dataset
# - Edit silver/ml_training/ml_training_payment_pred.sql
# - dbt run --select silver.ml_training

# 3. Train locally
# python scripts/train_payment_model.py

# 4. Push & open PR
git push origin feature/ml-payment-prediction

# On PR:
# - CI runs: dbt test --select silver.*
# - CI runs: dbt docs generate
# - Requires code review from ML Lead
# - Merge to main

# On main merge:
# - CD trigger: dbt build
# - CD trigger: Airflow dag update
# - CD trigger: Model retrain (if features changed)
```

---

## 🎯 USE CASES MAPPING

### **UC05: AR Management**
```sql
-- Query Gold (not Silver!)
select
  f.invoice_id,
  d.customer_code,
  f.invoice_amount,
  f.due_date,
  f.days_overdue,
  f.is_high_risk,
  s.predicted_payment_date,
  s.prediction_confidence
from gold.fact_ar_invoices f
join gold.dim_ar_customer d on f.customer_key = d.ar_customer_key
left join gold.score_payment_pred s on f.invoice_id = s.invoice_id
where f.is_high_risk = true
order by f.days_overdue desc
```

### **UC09: Forecast Cashflow**
```sql
-- Combine payment prediction + Silver features
select
  s.predicted_payment_date,
  sum(f.invoice_amount) as predicted_cash_in
from silver.ml_training_payment_pred f
join gold.score_payment_pred s on f.invoice_id = s.invoice_id
group by s.predicted_payment_date
order by s.predicted_payment_date
```

### **UC10: Anomaly Detection**
```sql
-- Compare actual vs predicted (via ML scores)
select
  s.predicted_payment_date,
  f.payment_date,
  datediff('day', s.predicted_payment_date, f.payment_date) as prediction_error_days,
  case 
    when abs(datediff('day', s.predicted_payment_date, f.payment_date)) > 14 then 'anomaly'
    else 'normal'
  end as flag
from gold.fact_ar_invoices f
join gold.score_payment_pred s on f.invoice_id = s.invoice_id
where f.payment_date is not null
  and abs(datediff('day', s.predicted_payment_date, f.payment_date)) > 7
```

---

## ✅ DEFINITION OF DONE

### **Silver Layer (Feature Store)**
- [ ] All base staging tables cleaned & Vietnamized
- [ ] Feature engineering tables created with business logic
- [ ] Training datasets have correct grain (no data leakage)
- [ ] Great Expectations quality rules written
- [ ] dbt tests for distribution shift detection
- [ ] Feature metadata documented (owner, SLA, update frequency)
- [ ] `dbt test` pass on all Silver models

### **Gold Layer (Analytics & Serve)**
- [ ] Conformed dimensions (SCD Type 0, 1, 2 as needed)
- [ ] Fact tables with surrogate keys to dims
- [ ] Link tables for reconciliation
- [ ] KPI marts pre-calculated for BI
- [ ] ML score serve tables with version tracking
- [ ] Row-level security configured
- [ ] `dbt test` pass on all Gold models

### **ML Pipeline (Orchestration)**
- [ ] Airflow DAG for data quality → training → inference
- [ ] MLflow experiment tracking for model versions
- [ ] Guardrails: Great Expectations + dbt tests
- [ ] CI/CD for feature changes (code review required)
- [ ] Model artifact versioning (MLflow or DVC)
- [ ] Batch inference writes scores to Gold daily
- [ ] Monitoring: prediction accuracy on holdout set

### **Kaggle Invoices Integration**
- [ ] Download script with Kaggle API
- [ ] Bronze: Raw CSVs in MinIO
- [ ] Silver: `stg_ar_invoices_vn` with all fields normalized
- [ ] Gold: `fact_ar_invoices` + `dim_ar_customer`
- [ ] KPI: `kpi_ar_dso_analysis` in Metabase
- [ ] ML training dataset includes Kaggle invoices
- [ ] `dbt test` pass with 500k+ rows

### **Documentation**
- [ ] README: Feature Store catalog with lineage
- [ ] dbt docs: `dbt docs generate` published
- [ ] ML handbook: Model training workflow, evaluation metrics
- [ ] Data dictionary: All columns, transformations, freshness
- [ ] Glossary: Terms (DSO, overdue, MAPE, etc.)

---

## 🚀 EXECUTION CHECKLIST

```bash
# 1. Setup Kaggle API
pip install kaggle
# ~/.kaggle/kaggle.json (get from kaggle.com/settings/account)

# 2. Add Kaggle dataset to Airflow
# - Create ingest_kaggle_invoices.py DAG
# - Test manually: python scripts/test_kaggle_download.py

# 3. Create Silver feature layers
dbt run --select silver.features
dbt run --select silver.ml_training
dbt test --select silver.*

# 4. Create Gold AR layers
dbt run --select gold.dims.dim_ar_customer
dbt run --select gold.facts.fact_ar_invoices
dbt run --select gold.kpi.kpi_ar_dso_analysis
dbt test --select gold.*

# 5. Setup ML pipeline
# - MLflow server: mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root s3://sme-lake/mlflow
# - Create training scripts (Prophet, XGBoost, etc.)
# - Deploy Airflow DAG: ml_training_daily

# 6. Deploy ML score serving
# - dbt run --select gold.ml_scores
# - Airflow: batch_inference → score writing

# 7. Monitor & validate
dbt build --selector build_warehouse
```

---

## � CẤU TRÚC THƯ MỤC DỰ ÁN

```
sme_pulse/
│
├─ README.md
├─ dbt_project.yml                    # ⭐ Config chính
├─ profiles.yml                       # Trino connection
├─ packages.yml                       # dbt-utils, etc.
├─ selectors.yml                      # Build workflow
│
├─ seeds/                             # 🌱 Reference data
│  ├─ seed_channel_map.csv
│  ├─ seed_payment_method_map.csv
│  ├─ seed_carrier_map.csv
│  ├─ seed_fx_rates.csv
│  ├─ seed_provinces.csv
│  └─ seed_vn_holidays.csv
│
├─ models/
│  │
│  ├─ bronze.yml                      # 🔌 Source declarations
│  │
│  ├─ silver/                         # 🥈 Feature Store Layer
│  │  ├─ _silver__models.yml          # Properties & tests
│  │  │
│  │  ├─ staging/
│  │  │  ├─ stg_orders_vn.sql         # Orders cleaned
│  │  │  ├─ stg_payments_vn.sql       # Payments cleaned
│  │  │  ├─ stg_shipments_vn.sql      # Shipments cleaned
│  │  │  ├─ stg_bank_txn_vn.sql       # Bank transactions
│  │  │  └─ stg_ar_invoices_vn.sql    # ⭐ NEW: Kaggle invoices
│  │  │
│  │  ├─ features/                    # 🔄 ML Feature Engineering
│  │  │  ├─ ftr_customer_behavior.sql # RFM, segment, payment history
│  │  │  ├─ ftr_invoice_risk.sql      # DSO, overdue flags
│  │  │  ├─ ftr_payment_pattern.sql   # Payment method, timing
│  │  │  ├─ ftr_seasonality.sql       # Temporal features
│  │  │  └─ ftr_macroeconomic.sql     # WB indicators joined
│  │  │
│  │  └─ ml_training/                 # 🎯 Training Datasets (no leakage)
│  │     ├─ ml_training_payment_pred.sql
│  │     ├─ ml_training_ar_scoring.sql
│  │     └─ ml_training_cashflow_fcst.sql
│  │
│  └─ gold/                           # 🥇 Analytics Ready Layer
│     ├─ _gold__models.yml            # Properties & tests
│     │
│     ├─ dims/                        # 📊 Conformed Dimensions
│     │  ├─ dim_date.sql              # SCD Type 0 (slowly changing)
│     │  ├─ dim_customer.sql          # SCD Type 2 (with history)
│     │  ├─ dim_product.sql           # SCD Type 1 (latest)
│     │  ├─ dim_channel.sql           # SCD Type 0
│     │  ├─ dim_payment_method.sql    # SCD Type 0
│     │  ├─ dim_carrier.sql           # SCD Type 0
│     │  ├─ dim_geo.sql               # SCD Type 1
│     │  └─ dim_ar_customer.sql       # ⭐ NEW: SCD Type 2 for AR
│     │
│     ├─ facts/                       # 📈 Fact Tables (Grain = detail)
│     │  ├─ fact_orders.sql           # 1 row = 1 order line
│     │  ├─ fact_payments.sql         # 1 row = 1 payment
│     │  ├─ fact_shipments.sql        # 1 row = 1 shipment
│     │  ├─ fact_bank_txn.sql         # 1 row = 1 bank txn
│     │  └─ fact_ar_invoices.sql      # ⭐ NEW: 1 row = 1 invoice
│     │
│     ├─ links/                       # 🔗 Reconciliation Bridges (M:N)
│     │  ├─ link_order_payment.sql    # Orders ↔ Payments
│     │  ├─ link_payment_bank.sql     # Payments ↔ Bank
│     │  └─ link_order_shipment.sql   # Orders ↔ Shipments
│     │
│     ├─ kpi/                         # 📊 KPI Marts (for BI dashboards)
│     │  ├─ kpi_daily_revenue.sql     # Daily revenue + cost
│     │  ├─ kpi_payment_success_rate.sql
│     │  ├─ kpi_reconciliation_daily.sql
│     │  └─ kpi_ar_dso_analysis.sql   # ⭐ NEW: DSO, overdue analysis
│     │
│     └─ ml_scores/                   # 🤖 ML Predictions Served
│        ├─ score_payment_pred.sql    # Predicted payment date
│        ├─ score_ar_priority.sql     # Collection priority score
│        ├─ score_churn_risk.sql      # Customer churn risk
│        └─ score_cashflow_fcst.sql   # Predicted cash-in
│
├─ macros/                            # 🔧 Reusable SQL functions
│  ├─ get_custom_schema.sql
│  └─ dbt_utils_override/             # Override dbt-utils macros
│     └─ trino__get_tables_by_pattern_sql.sql
│
├─ tests/                             # 🧪 Custom dbt tests
│  ├─ feature_store_quality.sql       # Feature stability checks
│  ├─ fact_grain_tests.sql            # Verify fact table grain
│  └─ link_reconciliation_tests.sql   # Link table validation
│
├─ analyses/                          # 📊 Ad-hoc analysis queries
│  └─ dso_trend_analysis.sql
│
└─ docs/                              # 📚 Documentation
   ├─ architecture.md
   ├─ feature_catalog.md
   └─ data_dictionary.md
```

---

## 🔄 DATA FLOW DIAGRAMS

### **Diagram 1: End-to-End Data Flow (Bronze → Silver → Gold)**

```
┌────────────────────┐
│  EXTERNAL SOURCES  │
├────────────────────┤
│ • CSV uploads      │
│ • APIs (World Bank)│
│ • Kaggle datasets  │
│ • Bank feeds       │
└─────────┬──────────┘
          │
          ↓
┌────────────────────────────────────────┐
│      BRONZE LAYER (Raw, Immutable)     │
├────────────────────────────────────────┤
│ • sales_snapshot_raw       (orders)    │
│ • payments_raw             (payments)  │
│ • shipments_raw            (shipments) │
│ • bank_txn_raw             (bank)      │
│ • kaggle_invoices_raw      (invoices) ⭐
└─────────────────┬──────────────────────┘
                  │ (Airflow: dbt run)
                  ↓
┌──────────────────────────────────────────────────┐
│   SILVER LAYER (Feature Store - Training Truth)  │
├──────────────────────────────────────────────────┤
│                                                  │
│  Staging Tables (Cleaned & Typed)                │
│  ├─ stg_orders_vn                                │
│  ├─ stg_payments_vn                              │
│  ├─ stg_shipments_vn                             │
│  ├─ stg_bank_txn_vn                              │
│  └─ stg_ar_invoices_vn                    ⭐     │
│                                                  │
│  Feature Engineering (Row-level)                 │
│  ├─ ftr_customer_behavior (1 row/customer)      │
│  ├─ ftr_invoice_risk (1 row/invoice)            │
│  ├─ ftr_payment_pattern (1 row/customer)        │
│  └─ ftr_seasonality (1 row/day)                 │
│                                                 │
│  ML Training Datasets (Fact + Features)         │
│  ├─ ml_training_payment_pred                    │
│  ├─ ml_training_ar_scoring                      │
│  └─ ml_training_cashflow_fcst                   │
└────────┬──────────────────────────────┬─────────┘
         │ (dbt run --select gold.*)    │
         ↓                              ↓
    ┌──────────────┐          ┌─────────────────────┐
    │ Gold: BI/KPI │          │ ML Pipeline (ext.)  │
    ├──────────────┤          ├─────────────────────┤
    │ • dims       │          │ • Data QC (GX)      │
    │ • facts      │          │ • Feature prep      │
    │ • kpis       │          │ • Model training    │
    │ • links      │          │ • Inference         │
    └──────────────┘          └────────┬────────────┘
         ↑                             │
         │                            ↓
         │                    ┌────────────────────┐
         │                    │ ML Scores (temp)   │
         │                    ├────────────────────┤
         │                    │ • predictions      │
         │                    │ • confidence       │
         │                    │ • version          │
         │                    └─────────┬──────────┘
         │                             │
         │                    (dbt run --select gold.ml_scores)
         │                             │
         └─────────────────────────────┘
                        │
                        ↓
         ┌──────────────────────────┐
         │   GOLD ML SCORES SERVE   │
         ├──────────────────────────┤
         │ • score_payment_pred     │
         │ • score_ar_priority      │
         │ • score_churn_risk       │
         │ • score_cashflow_fcst    │
         └──────────┬───────────────┘
                    │
                    ↓
         ┌──────────────────────────┐
         │  BI TOOLS & DASHBOARDS   │
         ├──────────────────────────┤
         │ • Metabase               │
         │ • Looker                 │
         │ • Power BI               │
         │ • APIs                   │
         └──────────────────────────┘
```

### **Diagram 2: Feature Store Design Pattern**

```
DATA SCIENTIST WORKFLOW
========================

    ┌─────────────────────────────────────────┐
    │    Silver: Feature Store (Training)     │
    ├─────────────────────────────────────────┤
    │                                         │
    │  ┌──────────────────────────────────┐   │
    │  │ stg_orders_vn                    │   │
    │  │ (raw staging, Vietnamized)       │   │
    │  └────────────┬─────────────────────┘   │
    │               │                         │
    │               ↓                         │
    │  ┌──────────────────────────────────┐   │
    │  │ ftr_customer_behavior            │   │
    │  │ • RFM: Recency, Frequency, Money │   │
    │  │ • Payment rate, customer segment │   │
    │  │ • Churn signals, LTV             │   │
    │  └────────────┬─────────────────────┘   │
    │               │                         │
    │               ↓                         │
    │  ┌──────────────────────────────────┐   │
    │  │ ml_training_payment_pred         │   │
    │  │ • Features: 30+ columns          │   │
    │  │ • Label: days_to_pay             │   │
    │  │ • No data leakage                │   │
    │  │ • Grain: 1 row = 1 invoice      │   │
    │  │ • 500k+ rows (Kaggle history)    │   │
    │  └────────────┬─────────────────────┘   │
    │               │                         │
    └───────────────┼─────────────────────────┘
                    │
                    │ (Export to CSV / Pandas)
                    ↓
         ┌──────────────────────────┐
         │  MLflow Experiment       │
         ├──────────────────────────┤
         │ • Train: Prophet, XGBoost│
         │ • Eval: MAPE, RMSE       │
         │ • Log: Artifacts, model  │
         │ • Version: Git hash      │
         └──────────┬───────────────┘
                    │
                    ↓
         ┌──────────────────────────┐
         │ Model Registry           │
         ├──────────────────────────┤
         │ • Champion model         │
         │ • Production stage       │
         │ • Version: v1.2.3        │
         └──────────┬───────────────┘
                    │
                    ↓
         ┌──────────────────────────┐
         │ Batch Inference          │
         ├──────────────────────────┤
         │ • Load model v1.2.3      │
         │ • Score on Silver feats  │
         │ • Write predictions      │
         └──────────┬───────────────┘
                    │
                    ↓
    ┌──────────────────────────────┐
    │  Gold: ML Scores Table       │
    ├──────────────────────────────┤
    │ • score_payment_pred         │
    │ • 1 row = 1 invoice          │
    │ • predicted_date, confidence │
    │ • model_version, timestamp   │
    └──────────┬───────────────────┘
               │
               ↓
    ┌──────────────────────────────┐
    │  dbt Tests (Gold)            │
    ├──────────────────────────────┤
    │ ✅ Not null scores           │
    │ ✅ Confidence in [0,1]       │
    │ ✅ Recent predictions        │
    └──────────────────────────────┘
```

### **Diagram 3: Silver vs Gold Layer Separation**

```
┌─────────────────────────────────────────────────────────┐
│                 FEATURE STORE (SILVER)                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Purpose: Training Machine Learning Models              │
│  ════════════════════════════════════════               │
│                                                         │
│  ✅ Row-level data (no aggregation)                     │
│  ✅ Historical data (2-3 years)                         │
│  ✅ Feature versioning (Git tracked)                    │
│  ✅ Detailed values (raw features)                      │
│  ✅ Can change frequently (refactoring)                 │
│  ✅ Data Scientists access directly                     │
│  ✅ Training labels included                            │
│  ✅ No data leakage controls (in model)                 │
│                                                         │
│  Example: ftr_customer_behavior                         │
│  ┌──────────────────────────────────┐                   │
│  │ customer_code   | payment_comp_rt │ updated_at       │
│  ├──────────────────────────────────┤                   │
│  │ CUST001         | 0.95            │ 2025-11-01      │
│  │ CUST001         | 0.93            │ 2025-10-01 (v2) │
│  │ CUST002         | 0.87            │ 2025-11-01      │
│  └──────────────────────────────────┘                   │
│                                                         │
│  SLA: Hourly refresh, 99% availability                  │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              ANALYTICS SERVE LAYER (GOLD)               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Purpose: Business Intelligence & KPI Dashboards       │
│  ═══════════════════════════════════════                │
│                                                         │
│  ✅ Pre-calculated aggregates (daily/weekly)            │
│  ✅ Denormalized Star schema                            │
│  ✅ Model predictions + scores served                   │
│  ✅ Optimized for BI tools query speed                  │
│  ✅ Stable structure (rarely change)                    │
│  ✅ Row-level security policies                         │
│  ✅ No training labels                                  │
│  ✅ BI Analysts access (not researchers)                │
│                                                         │
│  Example: kpi_daily_revenue                            │
│  ┌──────────────────────────────────┐                   │
│  │ date_key | total_revenue | growth │                  │
│  ├──────────────────────────────────┤                   │
│  │ 20251101 | 5,234,567,890  | +12% │                  │
│  │ 20251031 | 4,664,820,123  | +8%  │                  │
│  │ 20251030 | 4,319,084,932  | -3%  │                  │
│  └──────────────────────────────────┘                   │
│                                                         │
│  SLA: < 5s query latency, 99.9% availability            │
│                                                         │
└─────────────────────────────────────────────────────────┘

KEY DIFFERENCES
═══════════════
┌──────────────────┬──────────────────┬───────────────────┐
│ Aspect           │ Silver (Feature) │ Gold (Analytics)  │
├──────────────────┼──────────────────┼───────────────────┤
│ Grain            │ Row-level detail │ Aggregated daily  │
│ Ownership        │ Data Science     │ BI/Analytics      │
│ Change Frequency │ Often (iterative)│ Rarely (stable)   │
│ Query Performance│ N/A (batch)      │ < 5s (online)     │
│ Data Loss        │ No (raw)         │ Lossy (aggregate) │
│ Access Pattern   │ Full table read  │ WHERE/GROUP BY    │
│ Size             │ Large (all hist) │ Medium (summary)  │
│ Tests            │ Distribution     │ SLA monitoring    │
│ Version Control  │ Code + artifacts │ Schema only       │
└──────────────────┴──────────────────┴───────────────────┘
```

### **Diagram 4: ML Pipeline Orchestration (Airflow DAG)**

```
DAG: ml_training_daily (Runs 2 AM every day)
═════════════════════════════════════════════

┌─────────────────────────────────────┐
│  1. data_quality_check              │
│  ├─ Great Expectations              │
│  │  • Null rate < 5%                │
│  │  • Freshness ≤ 2 days            │
│  │  • Distribution shift (KL)       │
│  └─ Fail → Alert email, stop dag    │
└──────────────┬──────────────────────┘
               │ (success)
               ↓
┌──────────────────────────────────────────┐
│  2. feature_preparation                  │
│  ├─ Query Silver features (SQL)          │
│  │  • ml_training_payment_pred           │
│  │  • Filter: recent 30 days             │
│  ├─ Load to Pandas DataFrame             │
│  └─ Save to /tmp/training_data.csv       │
└──────────────┬───────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────┐
│  3. model_training                       │
│  ├─ Load CSV                             │
│  ├─ MLflow: Start experiment run         │
│  │  • Algo: Prophet + XGBoost            │
│  │  • Split: 80/20 train/val             │
│  │  • Cross-validation: 5-fold           │
│  ├─ Log metrics: MAPE, RMSE              │
│  ├─ Log artifacts: model.pkl             │
│  ├─ Log params: seasonality, trend       │
│  └─ Best model → Model Registry          │
└──────────────┬───────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────┐
│  4. model_evaluation                     │
│  ├─ Holdout test set evaluation          │
│  │  • MAPE < 15% ✅ Continue             │
│  │  • MAPE ≥ 15% ❌ Manual review        │
│  ├─ Logging: Test metrics                │
│  └─ Fail → SLA alert to ML team          │
└──────────────┬───────────────────────────┘
               │ (passed)
               ↓
┌──────────────────────────────────────────┐
│  5. batch_inference                      │
│  ├─ Load champion model v1.2.3           │
│  ├─ Score all active invoices (Silver)   │
│  │  • 50k+ invoices                      │
│  │  • Parallel processing (10 workers)    │
│  ├─ Generate: predicted_date, confidence │
│  └─ Write to temp table (Trino)          │
└──────────────┬───────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────┐
│  6. dbt_load_scores                      │
│  ├─ dbt run --select gold.ml_scores      │
│  │  • Load from temp → gold.score_*      │
│  │  • Partition by date_key              │
│  ├─ dbt test                             │
│  │  • Not null checks                    │
│  │  • Confidence ∈ [0,1]                 │
│  │  • Record count > 0                   │
│  └─ Success → Mark task complete         │
└──────────────┬───────────────────────────┘
               │
               ↓
         ┌──────────────┐
         │ 🟢 SUCCESS   │
         │ Scores live  │
         │ in Gold      │
         └──────────────┘
         
         Slack: "✅ Payment model v1.2.3 trained. MAPE=12.3%"
         Dashboard: Refresh predictions view
```

### **Diagram 5: Dependencies & DAG Build Order**

```
DEPENDENCY GRAPH (Layers & Order)
═════════════════════════════════

TIER 1: Seeds & Bronze
┌──────────────────────────┐
│ seed_*                   │ ← Reference data (no deps)
│ bronze.sales_snapshot_*  │ ← Raw data (external)
└──────────────┬───────────┘
               │
               ↓

TIER 2: Silver Staging (Parallel)
┌────────────────────────────────────────────────┐
│ ┌─stg_orders_vn                                │
│ ├─stg_payments_vn           (all independent)   │
│ ├─stg_shipments_vn                            │
│ ├─stg_bank_txn_vn                             │
│ └─stg_ar_invoices_vn        ⭐ NEW             │
└──────────────┬────────────────────────────────┘
               │
               ↓

TIER 3: Silver Features (Parallel)
┌────────────────────────────────────────────────┐
│ ┌─ftr_customer_behavior ← stg_orders, stg_pmt  │
│ ├─ftr_invoice_risk ← stg_ar_invoices           │
│ ├─ftr_payment_pattern ← stg_payments_vn        │
│ ├─ftr_seasonality ← stg_orders_vn              │
│ └─ftr_macroeconomic ← external data source     │
└──────────────┬────────────────────────────────┘
               │
               ↓

TIER 4: Silver ML Training Datasets
┌────────────────────────────────────────────────┐
│ ml_training_payment_pred                       │
│  ├─ Depends: ftr_customer_behavior             │
│  ├─ Depends: ftr_invoice_risk                  │
│  └─ Depends: ftr_payment_pattern               │
└──────────────┬────────────────────────────────┘
               │
               ↓

TIER 5: Gold Dimensions (Parallel)
┌────────────────────────────────────────────────┐
│ ┌─ dim_date          (no deps)                  │
│ ├─ dim_customer ← stg_orders_vn                │
│ ├─ dim_product ← stg_orders_vn                 │
│ ├─ dim_channel ← seed_channel_map              │
│ ├─ dim_payment_method ← seed_payment_*         │
│ ├─ dim_carrier ← seed_carrier_map              │
│ ├─ dim_geo ← seed_provinces                    │
│ └─ dim_ar_customer ← ftr_customer_behavior  ⭐ │
└──────────────┬────────────────────────────────┘
               │
               ↓

TIER 6: Gold Facts (Parallel, deps on Dims)
┌────────────────────────────────────────────────┐
│ ┌─ fact_orders ← stg_orders_vn, dim_channel    │
│ ├─ fact_payments ← stg_payments, dim_*         │
│ ├─ fact_shipments ← stg_shipments, dim_carrier │
│ ├─ fact_bank_txn ← stg_bank_txn, dim_date      │
│ └─ fact_ar_invoices ← ftr_invoice_risk, dims ⭐│
└──────────────┬────────────────────────────────┘
               │
               ↓

TIER 7: Gold Links (Parallel, deps on Facts)
┌────────────────────────────────────────────────┐
│ ├─ link_order_payment ← fact_orders, fact_pmt  │
│ ├─ link_payment_bank ← fact_payments, fact_txn │
│ └─ link_order_shipment ← fact_orders, fact_ship│
└──────────────┬────────────────────────────────┘
               │
               ↓

TIER 8: Gold KPIs (Parallel, deps on Facts/Links)
┌────────────────────────────────────────────────┐
│ ├─ kpi_daily_revenue ← fact_orders, dim_date   │
│ ├─ kpi_payment_success ← link_order_payment    │
│ ├─ kpi_reconciliation ← link_order_payment     │
│ └─ kpi_ar_dso ← fact_ar_invoices               │
└──────────────┬────────────────────────────────┘
               │
               ↓

TIER 9: Gold ML Scores (External, serial)
┌────────────────────────────────────────────────┐
│ (Written by Airflow ML pipeline)               │
│ ├─ score_payment_pred (via MLflow inference)   │
│ ├─ score_ar_priority                          │
│ ├─ score_churn_risk                           │
│ └─ score_cashflow_fcst                        │
└────────────────────────────────────────────────┘

EXECUTION COMMANDS
═════════════════

# PARALLEL (All at once - dbt handles deps)
dbt build

# SEQUENTIAL (Explicit)
dbt run --select silver.staging
dbt run --select silver.features
dbt run --select silver.ml_training
dbt run --select gold.dims
dbt run --select gold.facts
dbt run --select gold.links
dbt run --select gold.kpi

# WITH SELECTOR (Recommended)
dbt build --selector build_warehouse
```

---

## �📚 REFERENCE ARCHITECTURE

**Best Practices**:
- **Netflix**: Feature Store (Metaflow) → Distributed training → Batch serving
- **Uber**: Michelangelo: Feature store (Cassandra) → Distributed ML → Real-time serving
- **Airbnb**: Feature store with Spark SQL + ML pipeline orchestration

**Key Principle**: 
> *"Train on raw data (Silver), serve aggregated predictions (Gold)"* 

This separates concerns, enables reproducibility, and allows data science and BI to work independently.

---

**Document Version**: 2.0 (ML-First Architecture + Directory Structure)  
**Last Updated**: 2025-11-01  
**Status**: Ready for Implementation  
**Review Cycle**: Monthly (check for feature drift, model performance)
