{{ config(
    materialized='table',
    tags=['silver', 'staging', 'payments', 'app_db']
) }}

-- ===================================================================
-- STG_PAYMENTS_APP_DB: Silver layer – Payments từ App DB
-- Source: finance.payments (OLTP database)
-- Purpose: Clean & standardize payment data for analytics
-- ===================================================================

with src as (
    select * from {{ source('app_db', 'payments_app_db_raw') }}
),

-- Standardize and clean data
cleaned as (
    select
        id as payment_id,
        org_id,
        transaction_date,
        amount,
        payment_method,
        reference_code,
        notes,
        created_at,
        updated_at,
        current_timestamp as processed_at
    from src
    where
        org_id is not null
        and amount > 0  -- Only positive payments
),

-- Add row numbers for deduplication
final as (
    select
        row_number() over (partition by payment_id, org_id order by updated_at desc) as rn,
        *
    from cleaned
)

select
    payment_id,
    org_id,
    transaction_date,
    amount,
    payment_method,
    reference_code,
    notes,
    created_at,
    updated_at,
    processed_at
from final
where rn = 1  -- Keep latest version only
