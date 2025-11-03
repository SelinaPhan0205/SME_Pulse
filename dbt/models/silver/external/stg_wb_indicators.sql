{{ config(
    materialized = 'table',
    tags = ['silver', 'external', 'world_bank']
) }}

WITH source AS (
    SELECT * FROM {{ source('bronze', 'world_bank_indicators_raw') }}
    WHERE country_code = 'VNM' -- Chỉ lấy dữ liệu Việt Nam
),

cleaned AS (
    SELECT
        -- Indicator identification
        indicator_code,
        country_code,
        
        -- Time dimension
        CAST(year AS INTEGER) AS indicator_year,
        
        -- Metric value (handle NULL for missing data)
        CAST(value AS DOUBLE) AS indicator_value,
        
        -- Vietnamese names for indicators
        CASE indicator_code
            WHEN 'FP.CPI.TOTL.ZG' THEN 'Lạm phát hàng năm (%)'
            WHEN 'NY.GDP.MKTP.KD.ZG' THEN 'Tăng trưởng GDP thực (%)'
            WHEN 'SL.UEM.TOTL.ZS' THEN 'Tỷ lệ thất nghiệp (%)'
            ELSE indicator_code
        END AS indicator_name_vi,
        
        CASE indicator_code
            WHEN 'FP.CPI.TOTL.ZG' THEN 'Inflation (Annual %)'
            WHEN 'NY.GDP.MKTP.KD.ZG' THEN 'GDP Growth (Annual %)'
            WHEN 'SL.UEM.TOTL.ZS' THEN 'Unemployment Rate (%)'
            ELSE indicator_code
        END AS indicator_name_en,
        
        -- Data quality flags
        CASE 
            WHEN value IS NULL THEN TRUE
            ELSE FALSE
        END AS is_missing_data,
        
        -- Metadata
        ingested_at,
        CURRENT_TIMESTAMP AS transformed_at
        
    FROM source
)

SELECT * FROM cleaned
WHERE indicator_year >= 2015 -- Chỉ lấy dữ liệu từ 2015 trở lại đây (tránh data quá cũ)
ORDER BY indicator_code, indicator_year
