{{ config(
    materialized='table',
    tags=['feature_store', 'ml_training', 'payment_prediction']
) }}

-- ===================================================================
-- ML_TRAINING_PAYMENT_PRED: Bảng dữ liệu huấn luyện
-- Tập hợp tất cả feature và label (days_to_pay)
-- Chỉ chứa các hóa đơn ĐÃ THANH TOÁN
-- ===================================================================

with invoices as (
    -- 1. Nguồn chính: chứa label (days_to_pay)
    select * from {{ ref('ftr_invoice_risk') }}
    where 
        payment_date is not null -- CHỈ học từ hóa đơn đã thanh toán
        and days_to_pay >= 0       -- Bỏ dữ liệu lỗi (trả trước khi hóa đơn tạo)
        and days_to_pay <= 180     -- Bỏ outlier (quá 6 tháng)
),

customers as (
    -- 2. Đặc trưng về hành vi khách hàng
    select * from {{ ref('ftr_customer_behavior') }}
),

seasonality as (
    -- 3. Đặc trưng về mùa vụ, thời gian
    select * from {{ ref('ftr_seasonality') }}
),

macro_econ as (
    -- 4. Đặc trưng về kinh tế vĩ mô
    select * from {{ ref('ftr_macroeconomic') }}
)

-- 5. Lắp ráp bảng
select 
    -- A. ID (cho mục đích truy vết)
    i.invoice_id,
    i.cust_number,
    
    -- B. Label (ĐÁP ÁN)
    i.days_to_pay as target_days_to_pay,
    
    -- C. Features từ ftr_invoice_risk
    i.total_open_amount,
    i.is_overdue_30,
    i.is_overdue_60,
    i.invoice_size_bracket,
    i.business_code,
    i.cust_payment_terms,
    
    -- D. Features từ ftr_customer_behavior
    coalesce(c.recency_days, -1) as cust_recency_days,
    coalesce(c.frequency_ltm, 0) as cust_frequency_ltm,
    coalesce(c.monetary_ltm, 0) as cust_monetary_ltm,
    coalesce(c.customer_age_days, 0) as cust_age_days,
    c.customer_segment,
    
    -- E. Features từ ftr_seasonality (của ngày phát hành hóa đơn)
    s.day_of_week as invoice_day_of_week,
    s.day_of_month as invoice_day_of_month,
    s.month_of_year as invoice_month_of_year,
    s.quarter_of_year as invoice_quarter,
    s.is_weekend as invoice_is_weekend,
    s.is_holiday_vn as invoice_is_holiday,
    s.is_beginning_of_month as invoice_is_bof,
    s.is_end_of_month as invoice_is_eof,
    
    -- F. Features từ ftr_macroeconomic (của năm phát hành hóa đơn)
    coalesce(m.gdp_growth_annual_pct, 0) as macro_gdp_growth,
    coalesce(m.inflation_annual_pct, 0) as macro_inflation,
    
    current_timestamp as training_prepared_at

from invoices i

-- ⚠️ IMPORTANT: Join key mapping
-- i.cust_number (AR customers/B2B) từ ftr_invoice_risk
-- c.customer_code (Retail customers) từ ftr_customer_behavior
-- Nếu không có bảng mapping giữa AR và Retail customers, hãy kiểm tra xem chúng có cùng pool khách hàng không
-- Hoặc có thể bạn bạn muốn dùng feature khác (ví dụ: đặc trưng từ chính invoice thay vì customer)
left join customers c
    on cast(i.cust_number as varchar) = cast(c.customer_code as varchar)

-- JOIN yếu tố thời gian
left join seasonality s
    on i.invoice_date = s.date_actual

-- JOIN yếu tố vĩ mô
left join macro_econ m
    on year(i.invoice_date) = m.indicator_year