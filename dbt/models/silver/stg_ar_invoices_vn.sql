{{ config(
    materialized='table',
    tags=['silver', 'staging', 'ar_invoices']
) }}

-- depends_on: {{ ref('seed_fx_rates') }}

-- ===================================================================
-- STG_AR_INVOICES_VN: Silver layer – AR invoice data từ Bronze
-- Lọc cột quan trọng + chuẩn hóa tiền về VND
-- 
-- DATA ISSUES FIXED:
-- 1. invoice_id stored as DOUBLE (scientific notation) → convert to BIGINT
-- 2. baseline_create_date & due_in_date stored as DOUBLE (2.0200126E7) 
--    → convert to BIGINT (20200126) → parse as YYYYMMDD
-- 3. clear_date stored as VARCHAR ('2020-02-11 00:00:00')
--    → extract DATE part using substr
-- ===================================================================

with src as (
    select * from {{ source('bronze', 'ar_invoices_raw') }}
),

-- Bước 1: Chuẩn hóa dữ liệu đầu vào
norm as (
    select
        -- Fix scientific notation: 1.9304E9 → cast to bigint
        cast(cast(invoice_id as double) as bigint) as invoice_id_int,
        cust_number,
        business_code,
        invoice_currency,
        cust_payment_terms,
        cast(isOpen as boolean) as is_open,
        
        -- Convert DOUBLE to BIGINT để chuẩn bị parse ngày
        -- baseline_create_date: 2.0200126E7 → 20200126
        cast(cast(baseline_create_date as double) as bigint) as baseline_int,
        
        -- due_in_date: 2.020021E7 → 20200210
        cast(cast(due_in_date as double) as bigint) as due_int,
        
        -- clear_date: '2020-02-11 00:00:00' (đã đúng format)
        cast(clear_date as varchar) as clear_str,
        
        try_cast(total_open_amount as double) as total_open_amount_raw
    from src
    where total_open_amount is not null
),

-- Bước 2: Parse dates từ integer/string  
norm_dates as (
    select
        invoice_id_int,
        cust_number,
        business_code,
        invoice_currency,
        cust_payment_terms,
        is_open,
        
        -- Parse YYYYMMDD integer: 20200126 → DATE '2020-01-26'
        -- Extract year/month/day: YYYYMMDD / 10000 = YYYY, (YYYYMMDD % 10000) / 100 = MM, YYYYMMDD % 100 = DD
        date(
            cast(baseline_int / 10000 as varchar) || '-' ||
            lpad(cast((baseline_int % 10000) / 100 as varchar), 2, '0') || '-' ||
            lpad(cast(baseline_int % 100 as varchar), 2, '0')
        ) as baseline_raw,
        
        date(
            cast(due_int / 10000 as varchar) || '-' ||
            lpad(cast((due_int % 10000) / 100 as varchar), 2, '0') || '-' ||
            lpad(cast(due_int % 100 as varchar), 2, '0')
        ) as due_raw,
        
        -- Parse clear_date: '2020-02-11 00:00:00' → DATE (lấy 10 ký tự đầu)
        try_cast(substr(clear_str, 1, 10) as date) as clear_raw,
        
        total_open_amount_raw
    from norm
),

-- Bước 3: Format lại ngày về yyyy/MM/dd
norm_fmt as (
    select
        cast(invoice_id_int as varchar) as invoice_id,
        cust_number,
        business_code,
        invoice_currency,
        cust_payment_terms,
        is_open,
        
        -- Format thành string 'yyyy/MM/dd'
        date_format(baseline_raw, '%Y/%m/%d') as baseline_create_date,
        date_format(due_raw, '%Y/%m/%d') as due_in_date,
        date_format(clear_raw, '%Y/%m/%d') as clear_date,
        
        total_open_amount_raw
    from norm_dates
),

-- Bước 4: Lấy tỷ giá mới nhất
fx_latest as (
    select
        currency_code,
        rate_to_vnd,
        row_number() over (partition by currency_code order by effective_date desc) as rn
    from {{ ref('seed_fx_rates') }}
),

fx as (
    select
        currency_code,
        rate_to_vnd
    from fx_latest
    where rn = 1
),

-- Bước 4: Join tỷ giá + chuẩn hóa tiền tệ
final as (
    select
        n.invoice_id,
        n.cust_number,
        n.business_code,
        n.invoice_currency,
        n.cust_payment_terms,
        n.baseline_create_date,
        n.due_in_date,
        n.clear_date,
        n.is_open,
        round(n.total_open_amount_raw * coalesce(f.rate_to_vnd, 1), 0) as total_open_amount,
        current_timestamp as ingested_at
    from norm_fmt n
    left join fx f
        on upper(n.invoice_currency) = upper(f.currency_code)
)

select * from final