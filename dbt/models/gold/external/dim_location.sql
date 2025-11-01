{{
    config(
        materialized='table',
        tags=['gold', 'dimensions', 'external']
    )
}}

WITH source AS (
    SELECT * FROM {{ ref('stg_vietnam_locations') }}
),

-- Generate surrogate key for SCD Type 2 (future-proofing for location changes)
with_surrogate_key AS (
    SELECT
        -- Surrogate key (dbt_utils.generate_surrogate_key equivalent)
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
        
        -- District attributes
        district_name,
        district_division_type,
        district_codename,
        
        -- Province attributes
        province_name,
        province_division_type,
        province_codename,
        phone_code,
        
        -- Region attributes
        region_name,
        region_name_en,
        
        -- Business logic: classify into urban/rural
        CASE
            WHEN district_division_type IN ('Quận', 'Thành phố', 'Thị xã') THEN 'Thành thị'
            WHEN district_division_type IN ('Huyện') THEN 'Nông thôn'
            ELSE 'Khác'
        END AS urban_rural_classification,
        
        CASE
            WHEN district_division_type IN ('Quận', 'Thành phố', 'Thị xã') THEN 'Urban'
            WHEN district_division_type IN ('Huyện') THEN 'Rural'
            ELSE 'Other'
        END AS urban_rural_classification_en,
        
        -- Business logic: major cities flag
        CASE
            WHEN province_code IN (1, 48, 79, 92) THEN TRUE -- Hà Nội, Đà Nẵng, TP.HCM, Cần Thơ
            ELSE FALSE
        END AS is_major_city,
        
        -- SCD Type 2 fields (currently all active, ready for future updates)
        created_at AS valid_from,
        CAST(NULL AS TIMESTAMP) AS valid_to,
        TRUE AS is_current,
        
        -- Metadata
        created_at,
        CURRENT_TIMESTAMP AS updated_at
        
    FROM source
)

SELECT * FROM with_surrogate_key
ORDER BY region_name, province_code, district_code
