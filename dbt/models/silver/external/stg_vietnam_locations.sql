{{ config(
    materialized='table',
    tags=['silver', 'external', 'vietnam_geography']
) }}

SELECT * FROM {{ ref('seed_vietnam_locations') }}
