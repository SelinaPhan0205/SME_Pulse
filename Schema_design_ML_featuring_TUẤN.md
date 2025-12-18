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
│  │  ├─ dim_date, dim_customer, dim_product, ...             │
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

## 📚 REFERENCE ARCHITECTURE

**Best Practices**:
- **Netflix**: Feature Store (Metaflow) → Distributed training → Batch serving
- **Uber**: Michelangelo: Feature store (Cassandra) → Distributed ML → Real-time serving
- **Airbnb**: Feature store with Spark SQL + ML pipeline orchestration

**Key Principle**: 
> *"Train on raw data (Silver), serve aggregated predictions (Gold)"* 

This separates concerns, enables reproducibility, and allows data science and BI to work independently.

---

**Document Version**: 2.0 (ML-First Architecture)  
**Last Updated**: 2025-11-01  
**Status**: Ready for Implementation  
**Review Cycle**: Monthly (check for feature drift, model performance)
