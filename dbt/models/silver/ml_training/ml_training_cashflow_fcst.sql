{{ config(
    materialized='table',
    tags=['feature_store', 'ml_training', 'cashflow_forecast']
) }}

-- ===================================================================
-- ML_TRAINING_CASHFLOW_FCST: Bảng dữ liệu huấn luyện Prophet
-- Tập hợp dòng tiền thuần (net cashflow) theo ngày
-- Cấu trúc: ds (ngày), y (giá trị), và các regressors (biến ngoại sinh)
-- ===================================================================

with payments_in as (
    -- 1. Nguồn tiền vào (Bán lẻ)
    select 
        payment_date as ds,
        sum(amount_vnd) as cash_in
    from {{ ref('stg_payments_vn') }}
    where payment_status_std = 'PAID'
    group by 1
),

bank_movements as (
    -- 2. Nguồn tiền vào/ra (Ngân hàng)
    select 
        txn_date as ds,
        sum(case 
            when direction_in_out = 'in' then amount_vnd
            else 0 
        end) as cash_in,
        sum(case 
            when direction_in_out = 'out' then amount_vnd
            else 0 
        end) as cash_out
    from {{ ref('stg_bank_txn_vn') }}
    group by 1
),

-- (Bạn có thể UNION thêm stg_ar_invoices nếu clear_date là ngày tiền về)

daily_cashflow as (
    -- 3. Tổng hợp dòng tiền thuần theo ngày
    select
        coalesce(p.ds, b.ds) as ds,
        coalesce(p.cash_in, 0) + coalesce(b.cash_in, 0) as total_cash_in,
        coalesce(b.cash_out, 0) as total_cash_out,
        (coalesce(p.cash_in, 0) + coalesce(b.cash_in, 0)) - coalesce(b.cash_out, 0) as y -- Đây là cột 'y'
    from payments_in p
    full outer join bank_movements b on p.ds = b.ds
),

seasonality as (
    -- 4. Đặc trưng mùa vụ (Regressors)
    select * from {{ ref('ftr_seasonality') }}
),

macro_econ as (
    -- 5. Đặc trưng vĩ mô (Regressors)
    select * from {{ ref('ftr_macroeconomic') }}
)

-- 6. Lắp ráp bảng huấn luyện Prophet
select 
    d.ds,
    d.y,
    d.total_cash_in,
    d.total_cash_out,
    
    -- Regressors từ Seasonality
    s.is_weekend,
    s.is_holiday_vn,
    s.is_beginning_of_month,
    s.is_end_of_month,
    s.sin_month,
    s.cos_month,
    s.sin_day_of_week,
    s.cos_day_of_week,
    
    -- Regressors từ Macro (Join lùi 1 năm vì dữ liệu vĩ mô có độ trễ)
    coalesce(m.gdp_growth_annual_pct, 0) as macro_gdp_growth,
    coalesce(m.inflation_annual_pct, 0) as macro_inflation
    
from daily_cashflow d

left join seasonality s 
    on d.ds = s.date_actual

left join macro_econ m
    on year(d.ds) = m.indicator_year + 1 -- Giả định dữ liệu vĩ mô 2023 ảnh hưởng 2024
    
where d.ds is not null
order by d.ds asc