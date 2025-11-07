{{ config(
    materialized='incremental',
    unique_key='customer_id',
    on_schema_change='append_new_columns',
    tags=['feature_store', 'payment_features']
) }}

-- ===================================================================
-- FTR_PAYMENT_PATTERN: Đặc trưng về thói quen thanh toán
-- Phương thức ưa thích, tần suất
-- Key: customer_id (từ stg_payments_vn)
-- ===================================================================

with payment_history as (
    select
        customer_id,
        payment_method_code,
        payment_date,
        amount_vnd,
        payment_status_std,
        
        -- Tính khoảng cách giữa các lần thanh toán
        date_diff(
            'day',
            lag(payment_date) over (partition by customer_id order by payment_date),
            payment_date
        ) as days_between_payments
        
    from {{ ref('stg_payments_vn') }}
    where payment_status_std = 'PAID'
    
    {% if is_incremental() %}
    -- Chỉ tính toán cho các khách hàng có thanh toán mới hoặc cập nhật
    and customer_id in (
        select distinct customer_id 
        from {{ ref('stg_payments_vn') }} 
        where payment_date > (select max(ftr_updated_at) from {{ this }})
    )
    {% endif %}
),

aggregated as (
    select
        customer_id,
        
        -- Phương thức thanh toán ưa thích (phương thức xuất hiện nhiều nhất)
        array_agg(payment_method_code order by payment_method_code)[1] as preferred_payment_method,
        
        -- Chỉ số về thời gian
        avg(days_between_payments) as avg_days_between_payments,
        stddev(days_between_payments) as stddev_days_between_payments,
        min(days_between_payments) as min_days_between_payments,
        max(days_between_payments) as max_days_between_payments,
        
        -- Chỉ số về giá trị
        avg(amount_vnd) as avg_payment_amount,
        sum(amount_vnd) as total_payment_amount,
        count(*) as total_payment_count,
        
        current_timestamp as ftr_updated_at
        
    from payment_history
    group by customer_id
)

select * from aggregated