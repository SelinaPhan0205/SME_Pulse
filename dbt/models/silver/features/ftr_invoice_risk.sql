{{ config(
    materialized='incremental',
    unique_key='invoice_id',
    on_schema_change='append_new_columns',
    tags=['feature_store', 'ar_features']
) }}

-- ===================================================================
-- FTR_INVOICE_RISK: Đặc trưng rủi ro của hóa đơn AR
-- Tính toán DSO, aging, và các cờ rủi ro
-- Key: invoice_id
-- ===================================================================

with invoices as (
    select
        invoice_id,
        cust_number,
        business_code,
        invoice_currency,
        cust_payment_terms,
        is_open,
        total_open_amount,
        
        -- Chuyển đổi string 'YYYY/MM/DD' sang DATE (Trino dùng DATE_PARSE)
        date_parse(baseline_create_date, '%Y/%m/%d') as invoice_date,
        date_parse(due_in_date, '%Y/%m/%d') as due_date,
        date_parse(clear_date, '%Y/%m/%d') as payment_date
        
    from {{ ref('stg_ar_invoices_vn') }}
    
    {% if is_incremental() %}
    -- Chỉ xử lý các hóa đơn mới hoặc vừa được cập nhật
    where ingested_at > (select max(ftr_updated_at) from {{ this }})
    {% endif %}
),

risk_features as (
    select
        invoice_id,
        cust_number,
        business_code,
        invoice_currency,
        cust_payment_terms,
        is_open,
        total_open_amount,
        invoice_date,
        due_date,
        payment_date,
        
        -- Days Overdue (Số ngày quá hạn)
        -- Nếu đã thanh toán: tính số ngày trễ (payment_date - due_date)
        -- Nếu CHƯA thanh toán (is_open): tính số ngày trễ (current_date - due_date)
        case
            when payment_date is not null then date_diff('day', due_date, payment_date)
            when is_open = true then date_diff('day', due_date, current_date)
            else 0
        end as days_overdue,
        
        -- Days to Pay (Số ngày để thanh toán)
        case
            when payment_date is not null then date_diff('day', invoice_date, payment_date)
            else null
        end as days_to_pay,
        
        -- Invoice Aging (Tuổi của hóa đơn)
        date_diff('day', invoice_date, current_date) as aging_days,
        
        -- Cờ rủi ro (Risk Flags)
        case when date_diff('day', due_date, current_date) > 30 and is_open = true then 1 else 0 end as is_overdue_30,
        case when date_diff('day', due_date, current_date) > 60 and is_open = true then 1 else 0 end as is_overdue_60,
        case when date_diff('day', due_date, current_date) > 90 and is_open = true then 1 else 0 end as is_overdue_90,
        
        -- Phân nhóm giá trị hóa đơn
        case
            when total_open_amount < 1000000 then '1. Small'
            when total_open_amount < 20000000 then '2. Medium'
            when total_open_amount < 100000000 then '3. Large'
            else '4. Very Large'
        end as invoice_size_bracket,
        
        current_timestamp as ftr_updated_at
        
    from invoices
    where due_date is not null and invoice_date is not null
)

select * from risk_features