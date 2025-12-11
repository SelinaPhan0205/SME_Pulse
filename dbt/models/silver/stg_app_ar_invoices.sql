{{ config(materialized='table', tags=['silver', 'staging', 'app_db']) }}

WITH src AS (
    SELECT id, org_id, invoice_no, customer_id, issue_date, due_date,
           total_amount, paid_amount, status, created_at, updated_at
    FROM {{ source('bronze_app_db', 'ar_invoices_app') }}
    WHERE org_id IS NOT NULL
)

SELECT
    CAST(id AS VARCHAR) AS invoice_id,
    CAST(org_id AS VARCHAR) AS business_code,
    CAST(customer_id AS VARCHAR) AS cust_number,
    FORMAT_DATETIME(CAST(issue_date AS TIMESTAMP), 'yyyy/MM/dd') AS baseline_create_date,
    FORMAT_DATETIME(CAST(due_date AS TIMESTAMP), 'yyyy/MM/dd') AS due_in_date,
    CAST(total_amount AS DOUBLE) AS total_open_amount,
    CASE WHEN status IN ('draft','posted','overdue','partial') THEN TRUE ELSE FALSE END AS is_open,
    'VND' AS invoice_currency,
    updated_at
FROM src WHERE total_amount > 0