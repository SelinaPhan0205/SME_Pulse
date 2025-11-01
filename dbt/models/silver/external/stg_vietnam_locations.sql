{{
    config(
        materialized='table',
        tags=['external', 'vietnam_geography']
    )
}}

WITH provinces AS (
    SELECT
        CAST(province_code AS INTEGER) AS province_code,
        province_name,
        phone_code,
        division_type AS province_division_type,
        codename AS province_codename
    FROM {{ source('bronze', 'vietnam_provinces_raw') }}
),

districts AS (
    SELECT
        CAST(district_code AS INTEGER) AS district_code,
        district_name,
        CAST(province_code AS INTEGER) AS province_code,
        division_type AS district_division_type,
        codename AS district_codename
    FROM {{ source('bronze', 'vietnam_districts_raw') }}
),

-- Gán vùng địa lý (Bắc/Trung/Nam) dựa trên tỉnh
provinces_with_region AS (
    SELECT
        province_code,
        province_name,
        phone_code,
        province_division_type,
        province_codename,
        
        -- Phân vùng theo convention địa lý Việt Nam
        CASE
            -- Miền Bắc
            WHEN province_code IN (1, 2, 4, 6, 8, 10, 11, 12, 14, 15, 17, 19, 20, 22, 24, 25, 26, 27, 30, 33, 34, 35, 36) THEN 'Miền Bắc'
            -- Miền Trung (từ Thanh Hóa đến Bình Thuận)
            WHEN province_code IN (38, 40, 42, 44, 45, 46, 48, 49, 51, 52, 54, 56, 58, 60, 62) THEN 'Miền Trung'
            -- Miền Nam (từ Bình Phước trở vào)
            WHEN province_code IN (64, 66, 67, 68, 70, 72, 74, 75, 77, 79, 80, 82, 83, 84, 86, 87, 89, 91, 92, 93, 94, 95, 96) THEN 'Miền Nam'
            ELSE 'Không xác định'
        END AS region_name,
        
        CASE
            WHEN province_code IN (1, 2, 4, 6, 8, 10, 11, 12, 14, 15, 17, 19, 20, 22, 24, 25, 26, 27, 30, 33, 34, 35, 36) THEN 'North'
            WHEN province_code IN (38, 40, 42, 44, 45, 46, 48, 49, 51, 52, 54, 56, 58, 60, 62) THEN 'Central'
            WHEN province_code IN (64, 66, 67, 68, 70, 72, 74, 75, 77, 79, 80, 82, 83, 84, 86, 87, 89, 91, 92, 93, 94, 95, 96) THEN 'South'
            ELSE 'Unknown'
        END AS region_name_en
        
    FROM provinces
),

-- Join provinces and districts
final AS (
    SELECT
        -- District level
        d.district_code,
        d.district_name,
        d.district_division_type,
        d.district_codename,
        
        -- Province level
        p.province_code,
        p.province_name,
        p.province_division_type,
        p.province_codename,
        p.phone_code,
        
        -- Region level
        p.region_name,
        p.region_name_en,
        
        -- Metadata
        CURRENT_TIMESTAMP AS created_at
        
    FROM districts d
    INNER JOIN provinces_with_region p
        ON d.province_code = p.province_code
)

SELECT * FROM final
ORDER BY province_code, district_code
