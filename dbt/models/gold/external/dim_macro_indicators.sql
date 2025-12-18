{{ config(
    materialized = 'table',
    tags = ['gold', 'dimension', 'external']
) }}

WITH source AS (
    SELECT * FROM {{ ref('stg_wb_indicators') }}
),

-- Pivot indicators into columns for easier analysis
pivoted AS (
    SELECT
        indicator_year,
        
        -- Inflation (Lạm phát)
        MAX(CASE WHEN indicator_code = 'FP.CPI.TOTL.ZG' THEN indicator_value END) AS inflation_rate_pct,
        MAX(CASE WHEN indicator_code = 'FP.CPI.TOTL.ZG' THEN is_missing_data END) AS inflation_is_missing,
        
        -- GDP Growth (Tăng trưởng GDP)
        MAX(CASE WHEN indicator_code = 'NY.GDP.MKTP.KD.ZG' THEN indicator_value END) AS gdp_growth_pct,
        MAX(CASE WHEN indicator_code = 'NY.GDP.MKTP.KD.ZG' THEN is_missing_data END) AS gdp_is_missing,
        
        -- Unemployment (Thất nghiệp)
        MAX(CASE WHEN indicator_code = 'SL.UEM.TOTL.ZS' THEN indicator_value END) AS unemployment_rate_pct,
        MAX(CASE WHEN indicator_code = 'SL.UEM.TOTL.ZS' THEN is_missing_data END) AS unemployment_is_missing,
        
        -- Metadata
        MAX(transformed_at) AS transformed_at
        
    FROM source
    GROUP BY indicator_year
),

-- Calculate YoY changes for trend analysis
with_changes AS (
    SELECT
        indicator_year,
        
        -- Current year values
        inflation_rate_pct,
        gdp_growth_pct,
        unemployment_rate_pct,
        
        -- YoY changes (so với năm trước)
        inflation_rate_pct - LAG(inflation_rate_pct) OVER (ORDER BY indicator_year) AS inflation_yoy_change,
        gdp_growth_pct - LAG(gdp_growth_pct) OVER (ORDER BY indicator_year) AS gdp_yoy_change,
        unemployment_rate_pct - LAG(unemployment_rate_pct) OVER (ORDER BY indicator_year) AS unemployment_yoy_change,
        
        -- Data quality flags
        inflation_is_missing,
        gdp_is_missing,
        unemployment_is_missing,
        
        -- Overall data quality score (0-3, 3 = all data available)
        CASE
            WHEN inflation_is_missing THEN 0 ELSE 1
        END +
        CASE
            WHEN gdp_is_missing THEN 0 ELSE 1
        END +
        CASE
            WHEN unemployment_is_missing THEN 0 ELSE 1
        END AS data_quality_score,
        
        -- Metadata
        transformed_at,
        CURRENT_TIMESTAMP AS updated_at
        
    FROM pivoted
)

SELECT * FROM with_changes
ORDER BY indicator_year DESC