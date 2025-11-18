{{ config(
    materialized='table',
    tags=['feature_store', 'ml_scoring', 'payment_prediction']
) }}

-- ===================================================================
-- ML_TRAINING_AR_SCORING: Bảng dữ liệu dự đoán (Inference)
-- Tập hợp tất cả feature cho các hóa đơn ĐANG MỞ (chưa thanh toán)
-- KHÔNG CÓ LABEL
-- ===================================================================

with invoices as (
    -- 1. Nguồn chính: Hóa đơn CÒN MỞ
    select * from {{ ref('ftr_invoice_risk') }}
    where is_open = true -- CHỈ lấy hóa đơn còn nợ
),

customers as (
    -- 2. Đặc trưng về hành vi khách hàng
    select * from {{ ref('ftr_customer_behavior') }}
),

seasonality as (
    -- 3. Đặc trưng về mùa vụ, thời gian
    select * from {{ ref('ftr_seasonality') }}
)

-- macro_econ as (
--     -- 4. Đặc trưng về kinh tế vĩ mô
--     -- DISABLED: World Bank data not available
-- )

-- 5. Lắp ráp bảng
select 
    -- A. ID (cho mục đích truy vết)
    i.invoice_id,
    i.cust_number,
    
    -- B. Features từ ftr_invoice_risk
    i.total_open_amount,
    i.is_overdue_30,
    i.is_overdue_60,
    i.invoice_size_bracket,
    i.business_code,
    i.cust_payment_terms,
    
    -- C. Features từ ftr_customer_behavior
    coalesce(c.recency_days, -1) as cust_recency_days,
    coalesce(c.frequency_ltm, 0) as cust_frequency_ltm,
    coalesce(c.monetary_ltm, 0) as cust_monetary_ltm,
    coalesce(c.customer_age_days, 0) as cust_age_days,
    c.customer_segment,
    
    -- D. Features từ ftr_seasonality (của ngày phát hành hóa đơn)
    s.day_of_week as invoice_day_of_week,
    s.day_of_month as invoice_day_of_month,
    s.month_of_year as invoice_month_of_year,
    s.quarter_of_year as invoice_quarter,
    s.is_weekend as invoice_is_weekend,
    s.is_holiday_vn as invoice_is_holiday,
    s.is_beginning_of_month as invoice_is_bof,
    s.is_end_of_month as invoice_is_eof
    
    -- E. Features từ ftr_macroeconomic (DISABLED - World Bank data not available)
    -- coalesce(m.gdp_growth_annual_pct, 0) as macro_gdp_growth,
    -- coalesce(m.inflation_annual_pct, 0) as macro_inflation,
    
    -- current_timestamp as scoring_prepared_at

from invoices i

-- JOIN hồ sơ khách hàng
left join customers c
    on cast(i.cust_number as varchar) = cast(c.customer_code as varchar)

-- JOIN yếu tố thời gian
left join seasonality s
    on i.invoice_date = s.date_actual

-- JOIN yếu tố vĩ mô (DISABLED)
-- left join macro_econ m
--     on year(i.invoice_date) = m.indicator_year