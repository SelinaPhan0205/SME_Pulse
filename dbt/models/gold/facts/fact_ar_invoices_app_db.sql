{{ config(
    materialized='table',
    tags=['gold', 'fact', 'ar_analytics', 'app_db']
) }}

-- ===================================================================
-- FACT_AR_INVOICES_APP_DB: Gold layer – AR invoice analytics
-- Purpose: Pre-aggregated metrics for STEP 1 Analytics API
-- Grain: 1 row = 1 AR invoice
-- ===================================================================

with stg_invoices as (
    select * from {{ ref('stg_ar_invoices_app_db') }}
),

-- Aggregate allocations per invoice
allocations as (
    select
        ar_invoice_id,
        org_id,
        count(*) as allocation_count,
        sum(allocated_amount) as total_allocated,
        max(updated_at) as last_allocation_date
    from {{ ref('stg_payment_allocations_app_db') }}
    where ar_invoice_id is not null
    group by ar_invoice_id, org_id
),

-- Join invoices with allocations
enriched as (
    select
        inv.invoice_id,
        inv.org_id,
        inv.invoice_no,
        inv.customer_id,
        inv.issue_date,
        inv.due_date,
        inv.total_amount,
        inv.paid_amount,
        inv.remaining_amount,
        inv.status,
        inv.aging_bucket,
        inv.days_overdue,
        inv.is_overdue,
        inv.is_high_risk,
        
        -- Allocation metrics
        coalesce(alloc.allocation_count, 0) as payment_allocation_count,
        coalesce(alloc.total_allocated, 0) as payment_total_allocated,
        coalesce(alloc.last_allocation_date, inv.updated_at) as last_allocation_date,
        
        -- Collection rate
        case
            when inv.total_amount > 0 
            then round((CAST(inv.paid_amount AS DOUBLE) / CAST(inv.total_amount AS DOUBLE)) * 100, 2)
            else 0
        end as collection_rate,
        
        -- Days to collect
        case
            when inv.status = 'paid'
            then date_diff('day', inv.issue_date, CAST(inv.updated_at AS DATE))
            else null
        end as days_to_collect,
        
        -- Audit
        inv.created_at,
        inv.updated_at,
        inv.processed_at,
        current_timestamp as fact_created_at,
        'AR_INVOICES_APP_DB' as source_system
        
    from stg_invoices inv
    left join allocations alloc
        on inv.invoice_id = alloc.ar_invoice_id
        and inv.org_id = alloc.org_id
)

select * from enriched
