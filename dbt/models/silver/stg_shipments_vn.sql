{{ config(
    materialized='table',
    tags=['silver', 'shipments', 'feature_store']
) }}

-- ===================================================================
-- STG_SHIPMENTS_VN: Silver layer - Retail shipment/delivery data
-- Chuẩn hóa shipping data từ retail orders
-- ===================================================================

-- depends_on: {{ ref('seed_vietnam_locations') }}
-- depends_on: {{ ref('seed_carrier_map') }}

with src as (
  select * from {{ source('bronze', 'shipments_payments_raw') }}
),

-- Bước 1: Chuẩn hóa dữ liệu shipment
norm as (
  select
    order_id,  -- Link to payments
    {{ dbt_utils.generate_surrogate_key(['order_id']) }} as shipment_id_nat,
    
    -- Timing
    cast(order_date as date) as order_date,
    order_time as order_time,
    
    -- Customer info (for linking)
    customer_id,
    lower(trim(customer_email)) as email_norm,
    
    -- Shipping details
    coalesce(nullif(trim(carrier), ''), 'Unknown') as shipping_method_src,
    coalesce(nullif(trim(order_status), ''), 'Unknown') as order_status_src,
    
    -- Product info (what's being shipped)
    product_category,
    product_brand,
    product_type,
    product_name as products,
    
    -- Order value (for shipping cost analysis)
    cast(total_amount as decimal(18,2)) as order_value_foreign,
    coalesce(nullif(trim(shipping_country), ''), 'USA') as country_src,
    
    -- Customer satisfaction
    rating as ratings,
    feedback
    
  from src
),

-- Bước 2: Random assign Vietnam location (691 districts)
with_vn_location as (
  select
    n.*,
    -- Parse order_id string to integer, handle decimal format like '8691788.0'
    cast(split_part(order_id, '.', 1) as bigint) % 691 + 1 as location_row_num
  from norm n
),

-- Bước 3: Enrich với location + carrier mapping
vn as (
  select
    wl.shipment_id_nat,
    wl.order_id,
    wl.order_date,
    wl.order_time,
    
    -- Customer
    wl.customer_id,
    wl.email_norm,
    
    -- Delivery location (VN only)
    vloc.province_name as delivery_province,
    vloc.district_name as delivery_district,
    vloc.region as delivery_region,
    
    -- Carrier mapping (GHN, GHTK, VTP, VNP)
    coalesce(c.carrier_code, 'OTHER') as carrier_code,
    coalesce(c.carrier_name_vi, 'Đơn vị khác') as carrier_name_vi,
    coalesce(c.service_level, 'Standard') as service_level,
    wl.shipping_method_src,
    
    -- Delivery status standardization
    case 
      when lower(wl.order_status_src) in ('delivered', 'completed') then 'DELIVERED'
      when lower(wl.order_status_src) in ('shipped', 'in transit', 'out for delivery') then 'IN_TRANSIT'
      when lower(wl.order_status_src) in ('processing', 'pending', 'confirmed') then 'PROCESSING'
      when lower(wl.order_status_src) in ('cancelled', 'returned') then 'CANCELLED'
      else 'OTHER' 
    end as delivery_status_std,
    wl.order_status_src,
    
    -- Estimated delivery time (business logic based on carrier)
    case
      when c.service_level = 'SameDay' then 1
      when c.service_level = 'Express' then 2
      when c.service_level = 'Standard' then 5
      when c.service_level = 'Economy' then 10
      else 7  -- Default
    end as estimated_delivery_days,
    
    -- Delivery priority flag
    case
      when c.service_level in ('SameDay', 'Express') then true
      else false
    end as is_priority_shipping,
    
    -- Order value in VND (converted from foreign currency)
    round(wl.order_value_foreign * case 
      when wl.country_src = 'USA' then 24750.0
      when wl.country_src = 'UK' then 31850.0
      when wl.country_src in ('Germany', 'France', 'Italy', 'Spain', 'Netherlands') then 27150.0
      when wl.country_src = 'Australia' then 16750.0
      when wl.country_src = 'Canada' then 18500.0
      else 24750.0
    end, 0) as order_value_vnd,
    
    -- Shipping zone (for logistics optimization)
    case
      when vloc.region = 'Miền Bắc' then 'NORTH'
      when vloc.region = 'Miền Trung' then 'CENTRAL'
      when vloc.region = 'Miền Nam' then 'SOUTH'
      else 'OTHER'
    end as shipping_zone,
    
    -- Product details
    wl.product_category,
    wl.product_brand,
    wl.product_type,
    wl.products,
    
    -- Customer satisfaction
    wl.ratings,
    wl.feedback,
    
    -- Calculated fields for analytics
    case
      when wl.ratings >= 4.5 then 'EXCELLENT'
      when wl.ratings >= 3.5 then 'GOOD'
      when wl.ratings >= 2.5 then 'AVERAGE'
      else 'POOR'
    end as delivery_satisfaction_level
    
  from with_vn_location wl
  
  -- Join Vietnam locations
  left join (
    select row_number() over (order by province_code, district_code) as rn, *
    from {{ ref('seed_vietnam_locations') }}
  ) vloc
    on wl.location_row_num = vloc.rn
  
  -- Join carrier mapping
  left join {{ ref('seed_carrier_map') }} c
    on lower(wl.shipping_method_src) = lower(c.source_shipping_method)
)

select * from vn

