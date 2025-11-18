{{
    config(
        materialized='table',
        tags=['gold', 'dimensions', 'external']
    )
}}

-- Simplified dim_location using seed_vietnam_locations
-- Seed only has: province_code, province_name, district_code, district_name, region

WITH source AS (
    SELECT * FROM {{ ref('stg_vietnam_locations') }}
),

with_surrogate_key AS (
    SELECT
        -- Surrogate key
        TO_HEX(
            MD5(TO_UTF8(
                CAST(district_code AS VARCHAR) || '|' || 
                district_name || '|' || 
                CAST(province_code AS VARCHAR)
            ))
        ) AS location_key,
        
        -- Natural keys
        district_code,
        province_code,
        
        -- Attributes
        district_name,
        province_name,
        region AS region_name,
        
        -- Major cities flag
        CASE
            WHEN province_code IN (1, 48, 79, 92) THEN TRUE
            ELSE FALSE
        END AS is_major_city,
        
        -- Metadata
        CURRENT_TIMESTAMP AS created_at,
        CURRENT_TIMESTAMP AS updated_at
        
    FROM source
)

SELECT * FROM with_surrogate_key
ORDER BY region_name, province_code, district_code
