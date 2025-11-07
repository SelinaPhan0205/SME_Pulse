{{ config(
    materialized='incremental',
    unique_key='customer_code',
    on_schema_change='append_new_columns',
    tags=['feature_store', 'customer_features']
) }}

-- ===================================================================
-- FTR_CUSTOMER_BEHAVIOR: Đặc trưng hành vi khách hàng
-- Tính toán RFM, LTV, và các chỉ số thanh toán
-- Key: customer_code (từ stg_orders_vn)
-- ===================================================================

with orders as (
    select 
        customer_code,
        cast(order_date || '-01' as date) as order_date,  -- Chuyển 'YYYY-MM' thành 'YYYY-MM-01' rồi cast sang DATE
        revenue,
        qty
    from {{ ref('stg_orders_vn') }}
),

payments as (
    select 
        customer_id as customer_code, -- Giả định customer_id = customer_code
        payment_date,
        amount_vnd,
        payment_status_std
    from {{ ref('stg_payments_vn') }}
    where payment_status_std = 'PAID' -- Chỉ tính các khoản đã thanh toán
),

-- Tính toán chỉ số từ đơn hàng
customer_orders_agg as (
    select
        cast(customer_code as varchar) as customer_code,  -- Đảm bảo type consistency
        count(*) as total_orders_all_time,
        sum(revenue) as total_revenue_all_time,
        sum(qty) as total_qty_all_time,
        avg(revenue) as avg_order_value,
        max(order_date) as last_order_date,
        min(order_date) as first_order_date,
        
        -- LTM (Last 12 Months)
        sum(case 
            when order_date >= date_add('month', -12, current_date) then revenue 
            else 0 
        end) as total_revenue_ltm,
        
        count(case 
            when order_date >= date_add('month', -12, current_date) then 1
        end) as total_orders_ltm

    from orders
    group by 1
),

-- Tính toán chỉ số từ thanh toán
customer_payments_agg as (
    select
        cast(customer_code as varchar) as customer_code,  -- Đảm bảo type match với orders
        count(*) as total_payments_ltm,
        sum(amount_vnd) as total_paid_ltm,
        avg(amount_vnd) as avg_payment_value
    from payments
    where payment_date >= date_add('month', -12, current_date)
    group by 1
),

-- Kết hợp tất cả features
final as (
    select
        o.customer_code,
        
        -- Order Features
        o.total_orders_all_time,
        o.total_revenue_all_time,
        o.avg_order_value,
        o.last_order_date,
        o.first_order_date,
        date_diff('day', o.first_order_date, current_date) as customer_age_days,
        
        -- RFM Features (dựa trên LTM)
        date_diff('day', o.last_order_date, current_date) as recency_days,
        coalesce(o.total_orders_ltm, 0) as frequency_ltm,
        coalesce(o.total_revenue_ltm, 0) as monetary_ltm,
        
        -- Payment Features (từ stg_payments_vn)
        coalesce(p.total_payments_ltm, 0) as total_payments_ltm,
        coalesce(p.total_paid_ltm, 0) as total_paid_ltm,
        
        -- Payment Completion Rate (ví dụ: tỷ lệ đơn hàng có thanh toán)
        -- (Logic này cần được tinh chỉnh nếu có link_order_payment)
        case 
            when o.total_orders_ltm > 0 
            then round(1.0 * coalesce(p.total_payments_ltm, 0) / o.total_orders_ltm, 4)
            else 0 
        end as payment_completion_rate,
        
        -- Customer Segment (ví dụ đơn giản)
        case
            when o.total_revenue_ltm > 500000000 and o.total_orders_ltm > 10 then 'VIP'
            when o.total_revenue_ltm > 100000000 then 'High Value'
            when date_diff('day', o.last_order_date, current_date) > 90 then 'Inactive'
            else 'Regular'
        end as customer_segment,
        
        current_timestamp as ftr_updated_at

    from customer_orders_agg o
    left join customer_payments_agg p 
        on o.customer_code = p.customer_code -- Join quan trọng!

    {% if is_incremental() %}
    -- Lệnh này để update các customer đã có
    where o.customer_code in (
        select customer_code from {{ this }} 
        where cast(last_order_date as date) < date_add('day', -1, current_date)
    )
    {% endif %}
)

select * from final