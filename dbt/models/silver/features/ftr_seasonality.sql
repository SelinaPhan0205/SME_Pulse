{{ config(
    materialized='table',
    tags=['feature_store', 'temporal_features']
) }}

-- ===================================================================
-- FTR_SEASONALITY: Đặc trưng về thời gian, mùa vụ, lễ
-- Dùng dim_date đã xây dựng
-- Key: date_actual
-- ===================================================================

select 
    date_actual,
    date_key,
    day_of_week_num as day_of_week,
    day as day_of_month,
    day_of_year,
    week_of_year,
    month as month_of_year,
    quarter as quarter_of_year,
    year as year_actual,
    
    -- Cờ cho ngày cuối tuần
    is_weekend,
    
    -- Cờ cho ngày lễ (từ seed_vn_holidays)
    is_holiday as is_holiday_vn,
    
    -- Cờ cho đầu/cuối tháng (thường là ngày trả lương/thanh toán)
    case when day <= 3 then 1 else 0 end as is_beginning_of_month,
    case when day >= 28 then 1 else 0 end as is_end_of_month,
    
    -- Sin/Cos cho mùa vụ (giúp model hiểu tính tuần hoàn)
    sin(2 * pi() * day_of_year / 365.25) as sin_day_of_year,
    cos(2 * pi() * day_of_year / 365.25) as cos_day_of_year,
    sin(2 * pi() * month / 12) as sin_month,
    cos(2 * pi() * month / 12) as cos_month,
    sin(2 * pi() * day_of_week_num / 7) as sin_day_of_week,
    cos(2 * pi() * day_of_week_num / 7) as cos_day_of_week
    
from {{ ref('dim_date') }}