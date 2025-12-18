{{ config(
    materialized='table',
    tags=['gold', 'fact', 'payment_analytics', 'app_db']
) }}

-- ===================================================================
-- FACT_PAYMENTS_APP_DB: Gold layer – Payment analytics
-- Purpose: Pre-aggregated payment metrics for STEP 1 Analytics API
-- Grain: 1 row = 1 payment (with allocation summary)
-- ===================================================================

with stg_payments as (
    select * from {{ ref('stg_payments_app_db') }}
),

-- Aggregate allocations per payment
allocations as (
    select
        payment_id,
        org_id,
        count(*) as invoice_allocation_count,
        sum(allocated_amount) as total_allocated,
        min(created_at) as first_allocation_date,
        max(updated_at) as last_allocation_date
    from {{ ref('stg_payment_allocations_app_db') }}
    where payment_id is not null
    group by payment_id, org_id
),

-- Enrich payments with allocation info
enriched as (
    select
        pay.payment_id,
        pay.org_id,
        pay.transaction_date,
        pay.amount,
        pay.payment_method,
        pay.reference_code,
        
        -- Allocation metrics
        coalesce(alloc.invoice_allocation_count, 0) as invoice_count,
        coalesce(alloc.total_allocated, 0) as total_allocated,
        coalesce(alloc.first_allocation_date, pay.created_at) as first_allocation_date,
        coalesce(alloc.last_allocation_date, pay.updated_at) as last_allocation_date,
        
        -- Allocation efficiency
        case
            when pay.amount > 0
            then round((CAST(coalesce(alloc.total_allocated, 0) AS DOUBLE) / CAST(pay.amount AS DOUBLE)) * 100, 2)
            else 0
        end as allocation_rate,
        
        -- Unallocated amount (possibly pending)
        (pay.amount - coalesce(alloc.total_allocated, 0)) as unallocated_amount,
        
        -- Audit
        pay.created_at,
        pay.updated_at,
        pay.processed_at,
        current_timestamp as fact_created_at,
        'PAYMENTS_APP_DB' as source_system
        
    from stg_payments pay
    left join allocations alloc
        on pay.payment_id = alloc.payment_id
        and pay.org_id = alloc.org_id
)

select * from enriched
