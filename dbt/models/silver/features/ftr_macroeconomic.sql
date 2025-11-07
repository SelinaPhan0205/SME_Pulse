{{ config(
    materialized='table',
    tags=['feature_store', 'macro_features']
) }}

-- ===================================================================
-- FTR_MACROECONOMIC: Đặc trưng kinh tế vĩ mô (World Bank)
-- Pivot bảng stg_wb_indicators
-- Key: indicator_year
-- ===================================================================

with source as (
    select * from {{ ref('stg_wb_indicators') }}
)

select
    indicator_year,
    
    max(case 
        when indicator_code = 'NY.GDP.MKTP.KD.ZG' then indicator_value 
    end) as gdp_growth_annual_pct,
    
    max(case 
        when indicator_code = 'FP.CPI.TOTL.ZG' then indicator_value 
    end) as inflation_annual_pct,
    
    max(case 
        when indicator_code = 'SL.UEM.TOTL.ZS' then indicator_value 
    end) as unemployment_rate_pct
    
from source
group by 1
order by 1 desc