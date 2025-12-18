{{ config(
    materialized='table',
    tags=['silver', 'staging', 'payment_allocations', 'app_db']
) }}

-- ===================================================================
-- STG_PAYMENT_ALLOCATIONS_APP_DB: Silver layer – Payment allocations
-- Source: finance.payment_allocations (OLTP database)
-- Purpose: Clean payment-to-invoice mappings for reconciliation
-- ===================================================================

with src as (
    select * from {{ source('app_db', 'payment_allocations_app_db_raw') }}
),

-- Clean and standardize
cleaned as (
    select
        id as allocation_id,
        org_id,
        payment_id,
        ar_invoice_id,
        allocated_amount,
        notes,
        created_at,
        updated_at,
        current_timestamp as processed_at
    from src
    where
        org_id is not null
        and payment_id is not null
        and allocated_amount > 0
),

-- Add row numbers for deduplication
final as (
    select
        row_number() over (partition by allocation_id, org_id order by updated_at desc) as rn,
        *
    from cleaned
)

select
    allocation_id,
    org_id,
    payment_id,
    ar_invoice_id,
    allocated_amount,
    notes,
    created_at,
    updated_at,
    processed_at
from final
where rn = 1  -- Keep latest version only
