{{ config(
    materialized='table',
    tags=['silver', 'staging', 'ar_invoices', 'app_db'],
    schema='silver'
) }}

-- ===================================================================
-- STG_AR_INVOICES_APP_DB: Silver layer – AR invoices từ PostgreSQL App DB
-- Source: app_db.ar_invoices_app_db_raw (MinIO Parquet)
-- Purpose: Clean & standardize AR invoice data from transactional system
-- 
-- Transformation:
-- 1. Standardize date and numeric types
-- 2. Normalize status values (draft, posted, partial, paid, overdue, cancelled)
-- 3. Calculate aging and days overdue
-- 4. Flag high-risk invoices
-- 5. Handle NULL values and invalid records
-- ===================================================================

with src as (
    select * from {{ source('app_db', 'ar_invoices_app_db_raw') }}
),

-- Standardize and clean data
cleaned as (
    select
        id as invoice_id,
        org_id,
        invoice_no,
        customer_id,
        issue_date,
        due_date,
        total_amount,
        paid_amount,
        -- Standardize status (draft, posted, partial, paid, overdue, cancelled)
        lower(status) as status,
        notes,
        created_at,
        updated_at,
        
        -- Derived metrics
        (total_amount - paid_amount) as remaining_amount,
        
        -- Days overdue (0 if not due yet or fully paid)
        -- Days overdue
        case
            when status = 'paid' then 0
            when current_date > due_date then date_diff('day', due_date, current_date)
            else 0
        end as days_overdue,
        
        -- Aging bucket
        case
            when status = 'paid' then '0-30 days'
            when date_diff('day', due_date, current_date) <= 30 then '0-30 days'
            when date_diff('day', due_date, current_date) <= 60 then '31-60 days'
            when date_diff('day', due_date, current_date) <= 90 then '61-90 days'
            else '90+ days'
        end as aging_bucket,
        
        -- Risk flags
        case
            when status = 'paid' then false
            when current_date > due_date then true
            else false
        end as is_overdue,
        
        case
            when status = 'paid' then false
            when date_diff('day', due_date, current_date) > 90 then true
            else false
        end as is_high_risk,
        
        current_timestamp as processed_at
    from src
    where org_id is not null  -- Filter out rows without org
),

-- Add row numbers for deduplication
final as (
    select
        row_number() over (partition by invoice_id, org_id order by updated_at desc) as rn,
        *
    from cleaned
)

select
    invoice_id,
    org_id,
    invoice_no,
    customer_id,
    issue_date,
    due_date,
    total_amount,
    paid_amount,
    remaining_amount,
    status,
    aging_bucket,
    days_overdue,
    is_overdue,
    is_high_risk,
    notes,
    created_at,
    updated_at,
    processed_at
from final
where rn = 1  -- Keep latest version only
