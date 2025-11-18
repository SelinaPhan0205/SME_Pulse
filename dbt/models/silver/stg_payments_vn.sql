{{ config(
    materialized='table',
    tags=['silver', 'payments', 'feature_store']
) }}

-- ===================================================================
-- STG_PAYMENTS_VN: Silver layer - Retail payment transactions
-- Chuẩn hóa payment data từ retail orders với FX conversion sang VND
-- ===================================================================

with src as (
  select * from {{ source('bronze', 'shipments_payments_raw') }}
),

-- Bước 1: Chuẩn hóa dữ liệu gốc
norm as (
  select
    order_id,  -- Giữ lại để dùng cho random location
    {{ dbt_utils.generate_surrogate_key(['order_id']) }} as payment_id_nat,
    
    -- Timestamp processing
    cast(order_date as date) as transaction_date,
    order_time as transaction_time,
    
    -- Amount fields (ngoại tệ gốc - sẽ convert sang VND sau)
    cast(order_amount as decimal(18,2)) as amount_foreign,
    cast(total_amount as decimal(18,2)) as total_amount_foreign,
    
    -- Customer info
    customer_id,
    lower(trim(customer_email)) as email_norm,
    
    -- Original location (for reference only - will be replaced with VN location)
    coalesce(nullif(trim(shipping_country), ''), 'USA') as country_src,
    
    -- Payment info
    coalesce(nullif(trim(payment_method), ''), 'Unknown') as payment_method_src,
    coalesce(nullif(trim(order_status), ''), 'Unknown') as order_status_src,
    
    -- Shipping
    carrier as shipping_method_src,
    
    -- Product info
    product_category,
    product_brand,
    product_type,
    product_name as products,
    
    -- Other
    rating as ratings,
    feedback
    
  from src
),

-- Bước 2: Random assign Vietnam location cho mỗi transaction
-- Sử dụng MOD để phân bố đều các địa chỉ VN (691 districts)
with_vn_location as (
  select
    n.*,
    -- Random location based on order_id (691 total locations)
    -- Parse order_id string to integer, handle decimal format like '8691788.0'
    cast(split_part(order_id, '.', 1) as bigint) % 691 + 1 as location_row_num
  from norm n
),

-- Bước 3: Join với mapping tables + Vietnam locations
vn as (
  select
    wl.payment_id_nat,
    wl.transaction_date as payment_date,
    wl.transaction_time,
    
    -- Customer
    wl.customer_id,
    wl.email_norm,
    
    -- Vietnam Location (thay thế country nước ngoài)
    vloc.province_name,
    vloc.district_name,
    vloc.region,
    
    -- Payment method mapping
    coalesce(m.method_code, 'OTHER') as payment_method_code,
    coalesce(m.method_name_vn, 'Khác') as payment_method_name_vn,
    coalesce(m.is_digital, false) as is_digital_payment,
    wl.payment_method_src,
    
    -- Order status standardization
    case 
      when lower(wl.order_status_src) in ('shipped', 'delivered', 'paid', 'completed') then 'PAID'
      when lower(wl.order_status_src) in ('processing', 'pending') then 'PENDING'
      when lower(wl.order_status_src) in ('cancelled', 'refunded') then 'CANCELLED'
      else 'OTHER' 
    end as payment_status_std,
    wl.order_status_src,
    
    -- Convert foreign currency to VND
    -- Mapping: USA→USD, UK→GBP, Germany/France/Italy→EUR, Australia→AUD, Canada→CAD
    case 
      when wl.country_src = 'USA' then 'USD'
      when wl.country_src = 'UK' then 'GBP'
      when wl.country_src in ('Germany', 'France', 'Italy', 'Spain', 'Netherlands') then 'EUR'
      when wl.country_src = 'Australia' then 'AUD'
      when wl.country_src = 'Canada' then 'CAD'
      else 'USD'  -- Default
    end as currency_code,
    
    -- FX rates (average 2023-2024)
    case 
      when wl.country_src = 'USA' then 24750.0
      when wl.country_src = 'UK' then 31850.0
      when wl.country_src in ('Germany', 'France', 'Italy', 'Spain', 'Netherlands') then 27150.0
      when wl.country_src = 'Australia' then 16750.0
      when wl.country_src = 'Canada' then 18500.0
      else 24750.0
    end as fx_rate_to_vnd,
    
    -- Amounts in VND
    wl.amount_foreign,
    wl.total_amount_foreign,
    round(wl.amount_foreign * case 
      when wl.country_src = 'USA' then 24750.0
      when wl.country_src = 'UK' then 31850.0
      when wl.country_src in ('Germany', 'France', 'Italy', 'Spain', 'Netherlands') then 27150.0
      when wl.country_src = 'Australia' then 16750.0
      when wl.country_src = 'Canada' then 18500.0
      else 24750.0
    end, 0) as amount_vnd,
    round(wl.total_amount_foreign * case 
      when wl.country_src = 'USA' then 24750.0
      when wl.country_src = 'UK' then 31850.0
      when wl.country_src in ('Germany', 'France', 'Italy', 'Spain', 'Netherlands') then 27150.0
      when wl.country_src = 'Australia' then 16750.0
      when wl.country_src = 'Canada' then 18500.0
      else 24750.0
    end, 0) as total_amount_vnd,
    
    -- Shipping
    wl.shipping_method_src,
    
    -- Product
    wl.product_category,
    wl.product_brand,
    wl.product_type,
    wl.products,
    
    -- Other
    wl.ratings,
    wl.feedback
    
  from with_vn_location wl
  
  -- Join Vietnam locations (random distribution)
  left join (
    select row_number() over (order by province_code, district_code) as rn, *
    from {{ ref('seed_vietnam_locations') }}
  ) vloc
    on wl.location_row_num = vloc.rn
  
  -- Join payment method mapping
  left join {{ ref('seed_payment_method_map') }} m
    on lower(wl.payment_method_src) = lower(m.source_value)
)

select * from vn

