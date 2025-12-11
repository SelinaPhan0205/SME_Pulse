{{ config(materialized='table', tags=['silver', 'staging', 'app_db']) }}

WITH src AS (
    SELECT id, org_id, payment_date, amount, payment_method, reference_no, status, created_at, updated_at
    FROM {{ source('bronze_app_db', 'payments_app') }}
    WHERE org_id IS NOT NULL
)

SELECT
    CAST(id AS VARCHAR) AS payment_id,
    CAST(org_id AS VARCHAR) AS business_code,
    FORMAT_DATETIME(CAST(payment_date AS TIMESTAMP), 'yyyy/MM/dd') AS payment_date_formatted,
    CAST(amount AS DOUBLE) AS payment_amount,
    COALESCE(payment_method, 'CASH') AS payment_method_code,
    reference_no, status, updated_at
FROM src WHERE amount > 0