{{ config(
    materialized = 'table',
    tags = ['gold', 'dimension', 'scd0']
) }}

-- =====================================================================
-- 🗓️ DIM_DATE: Calendar dimension (SCD Type 0)
-- Purpose: Time intelligence for all facts
-- Grain: 1 row = 1 calendar day
-- =====================================================================

WITH date_spine AS (
  -- Generate date range: 2022-01-01 to 2026-12-31 (5 years)
  SELECT 
    SEQUENCE(DATE '2022-01-01', DATE '2026-12-31', INTERVAL '1' DAY) AS date_array
),

dates AS (
  SELECT date_val
  FROM date_spine
  CROSS JOIN UNNEST(date_array) AS t(date_val)
),

date_attributes AS (
  SELECT
    -- Surrogate Key (YYYYMMDD format)
    CAST(date_format(date_val, '%Y%m%d') AS BIGINT) AS date_key,
    
    -- Natural Key
    date_val AS date_actual,
    
    -- Date components
    YEAR(date_val) AS year,
    QUARTER(date_val) AS quarter,
    MONTH(date_val) AS month,
    DAY(date_val) AS day,
    DAY_OF_WEEK(date_val) AS day_of_week_num,
    DAY_OF_YEAR(date_val) AS day_of_year,
    WEEK(date_val) AS week_of_year,
    
    -- Named components (Vietnamese)
    CASE DAY_OF_WEEK(date_val)
      WHEN 1 THEN 'Thứ Hai'
      WHEN 2 THEN 'Thứ Ba'
      WHEN 3 THEN 'Thứ Tư'
      WHEN 4 THEN 'Thứ Năm'
      WHEN 5 THEN 'Thứ Sáu'
      WHEN 6 THEN 'Thứ Bảy'
      WHEN 7 THEN 'Chủ Nhật'
    END AS day_of_week_name_vi,
    
    CASE MONTH(date_val)
      WHEN 1 THEN 'Tháng 1'
      WHEN 2 THEN 'Tháng 2'
      WHEN 3 THEN 'Tháng 3'
      WHEN 4 THEN 'Tháng 4'
      WHEN 5 THEN 'Tháng 5'
      WHEN 6 THEN 'Tháng 6'
      WHEN 7 THEN 'Tháng 7'
      WHEN 8 THEN 'Tháng 8'
      WHEN 9 THEN 'Tháng 9'
      WHEN 10 THEN 'Tháng 10'
      WHEN 11 THEN 'Tháng 11'
      WHEN 12 THEN 'Tháng 12'
    END AS month_name_vi,
    
    CONCAT('Q', CAST(QUARTER(date_val) AS VARCHAR)) AS quarter_name,
    
    -- Fiscal attributes (assuming fiscal year = calendar year)
    YEAR(date_val) AS fiscal_year,
    QUARTER(date_val) AS fiscal_quarter,
    
    -- Business day flags
    CASE 
      WHEN DAY_OF_WEEK(date_val) IN (6, 7) THEN FALSE  -- Sat, Sun
      ELSE TRUE 
    END AS is_weekday,
    
    CASE 
      WHEN DAY_OF_WEEK(date_val) IN (6, 7) THEN TRUE 
      ELSE FALSE 
    END AS is_weekend,
    
    -- Period indicators
    CASE WHEN DAY(date_val) <= 10 THEN 'Early'
         WHEN DAY(date_val) <= 20 THEN 'Mid'
         ELSE 'Late'
    END AS month_period,
    
    -- First/last day flags
    CASE WHEN DAY(date_val) = 1 THEN TRUE ELSE FALSE END AS is_first_day_of_month,
    CASE WHEN date_val = LAST_DAY_OF_MONTH(date_val) THEN TRUE ELSE FALSE END AS is_last_day_of_month,
    
    -- Audit
    CURRENT_TIMESTAMP AS created_at
    
  FROM dates
)

SELECT 
  da.*,
  -- Join với Vietnamese holidays seed
  CASE WHEN h.date IS NOT NULL THEN TRUE ELSE FALSE END AS is_holiday,
  h.holiday_name,
  h.holiday_type
FROM date_attributes da
LEFT JOIN {{ ref('seed_vn_holidays') }} h
  ON da.date_actual = h.date