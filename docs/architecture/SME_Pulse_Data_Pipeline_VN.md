# SME Pulse – Thiết kế Data Pipeline chuẩn Việt Nam (Cho Copilot/AI Assistant)

> Mục tiêu: Mô tả **đầy đủ, có thể hành động ngay** để Copilot hiểu và hướng dẫn tớ triển khai **từ đầu đến cuối**: ingest → chuẩn hoá (Silver) → conformed **Dims/Facts** (Gold-ready) → **Link** đối soát → KPI/ML.  
> Yêu cầu: **1 dbt project**, **1 profile/connection**, **star schema chuẩn Việt**, **seeds Việt hoá**, có **lệnh chạy** và **DoD**.

---

## 0) Tổng quan kiến trúc

- **Nguồn (Bronze)**: 4 slice (Orders, Payments, Shipments, Bank CSV) – dữ liệu có thể là tiếng Anh/quốc tế.  
- **Silver (Chuẩn hoá Việt hoá)**: chuẩn kiểu dữ liệu, timezone `Asia/Ho_Chi_Minh`, chuyển đổi tiền tệ → VND, chuẩn danh mục VN (kênh, phương thức thanh toán, hãng vận chuyển), chuẩn hoá email/phone.  
- **Conformed Dimensions** *(chuẩn VN, dùng chung)*: `dim_date, dim_location, dim_customer, dim_product, dim_channel, dim_payment_method, dim_carrier`.  
- **Facts**: `fact_orders, fact_payments, fact_shipments, fact_bank_txn`.  
- **Link tables** (đối soát giữa các nguồn không có khoá chung):  
  - `link_order_payment` (Orders ↔ Payments)  
  - `link_payment_bank` (Payments ↔ Bank)  
  - `link_order_shipment` (Orders ↔ Shipments)  
- **Gold/KPI/ML** (downstream): `daily_revenue`, `payment_success_rate`, `reconciliation_daily`, `delivery_leadtime`, feed cho **Prophet**/**Isolation Forest**.

> Lý do có **Link**: dữ liệu khác nguồn thường **không có khoá chung** ổn định. Link lưu **kết quả đối soát** theo rule (số tiền gần bằng, cửa sổ thời gian, email/phone…), **audit được** và **không phá dữ liệu gốc**.

---

## 1) Chuẩn bị project & cấu trúc thư mục

```
sme_pulse/
├─ dbt_project.yml
├─ profiles.yml              # trino/postgres profile (1 target duy nhất)
├─ packages.yml              # dbt_utils,...
├─ seeds/
│  ├─ seed_channel_map.csv
│  ├─ seed_payment_method_map.csv
│  ├─ seed_carrier_map.csv
│  ├─ seed_fx_rates.csv
│  ├─ seed_provinces.csv
│  └─ seed_vn_holidays.csv
├─ models/
│  ├─ bronze.yml            # sources: sales_snapshot_raw, payments_raw,...
│  ├─ silver/
│  │  ├─ stg_orders_vn.sql
│  │  ├─ stg_payments_vn.sql
│  │  ├─ stg_shipments_vn.sql
│  │  └─ stg_bank_txn_vn.sql
│  ├─ dims/
│  │  ├─ dim_date.sql
│  │  ├─ dim_geo.sql
│  │  ├─ dim_customer.sql
│  │  ├─ dim_product.sql
│  │  ├─ dim_channel.sql
│  │  ├─ dim_payment_method.sql
│  │  └─ dim_carrier.sql
│  ├─ facts/
│  │  ├─ fact_orders.sql
│  │  ├─ fact_payments.sql
│  │  ├─ fact_shipments.sql
│  │  └─ fact_bank_txn.sql
│  ├─ links/
│  │  ├─ link_order_payment.sql
│  │  ├─ link_payment_bank.sql
│  │  └─ link_order_shipment.sql
│  └─ gold/
│     ├─ daily_revenue.sql
│     ├─ payment_success_rate.sql
│     ├─ reconciliation_daily.sql
│     └─ delivery_leadtime.sql
└─ macros/                   # nếu cần
```

**profiles.yml** (ví dụ Trino + Iceberg; đổi host/port theo docker compose của tớ)
```yaml
sme_pulse:
  target: trino
  outputs:
    trino:
      type: trino
      method: none
      host: trino
      port: 8080
      database: iceberg
      schema: silver
      threads: 4
```

**packages.yml**
```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.1.1", "<2.0.0"]
```

---

## 2) Seeds Việt hoá (CSV headers)

> Tạo trong `seeds/`, chạy `dbt seed` để sẵn sàng join map.

**seed_channel_map.csv**
```
source_value,channel_code,channel_name_vi
Online,Online,Online
CHTT,CHTT,Cửa hàng truyền thống
TGPP,TGPP,Thương gia phân phối
Retail,BANLE,Bán lẻ
```

**seed_payment_method_map.csv**
```
source_value,method_code,method_name_vi
Credit Card,card,Thẻ
Debit Card,card,Thẻ ghi nợ
Cash,cash,Tiền mặt
PayPal,transfer,Chuyển khoản
VietQR,vietqr,VietQR
MoMo,momo,MoMo
ZaloPay,zalopay,ZaloPay
```

**seed_carrier_map.csv**
```
source_shipping_method,carrier_code,carrier_name_vi,service_level
Same-Day,GHN,Giao Hàng Nhanh,SameDay
Express,GHTK,Giao Hàng Tiết Kiệm,Express
Standard,VTP,Viettel Post,Standard
```

**seed_fx_rates.csv**
```
ccy,rate_to_vnd,valid_from,valid_to
USD,24500,2025-01-01,2025-12-31
EUR,26500,2025-01-01,2025-12-31
GBP,30500,2025-01-01,2025-12-31
VND,1,2025-01-01,2025-12-31
```

**seed_provinces.csv** *(rút gọn ví dụ; thực tế gồm đủ 63 tỉnh/thành và alias)*  
```
province_code,province_name_en,province_name_vi,aliases,region_vi
HN,Hanoi,Hà Nội,"Hanoi;Ha Noi;HN",Đồng bằng sông Hồng
HCM,Ho Chi Minh,Hồ Chí Minh,"HCMC;Ho Chi Minh;TPHCM;SG",Đông Nam Bộ
DN,Da Nang,Đà Nẵng,"Danang;Da Nang;DN",Nam Trung Bộ
OTHER,Other,Khác,"",Khác
```

**seed_vn_holidays.csv**
```
date,holiday_name
2025-01-29,Tết Nguyên Đán (ví dụ)
2025-04-30,Giải phóng miền Nam
2025-05-01,Quốc tế Lao động
2025-09-02,Quốc khánh
```

---

## 3) Khai báo nguồn (Bronze sources)

**models/bronze.yml**
```yaml
version: 2
sources:
  - name: bronze
    schema: bronze
    tables:
      - name: sales_snapshot_raw     # Orders
      - name: payments_raw           # Payments
      - name: shipments_raw          # Shipments
      - name: bank_txn_raw           # Bank CSV
```
> 4 bảng raw này đã ingest sẵn từ Airflow/Airbyte/Python → Iceberg/Parquet.

---

## 4) Silver – Chuẩn hoá & Việt hoá

**stg_orders_vn.sql**
```sql
with src as (
  select * from {{ source('bronze','sales_snapshot_raw') }}
),
clean as (
  select
    try_to_date(concat(month, '01'), 'YYYYMMDD') as order_date,
    month as month_raw, week as week_raw,
    {{ dbt_utils.surrogate_key(['month','week','site','branch_id','customer_id','product_id']) }} as order_id_nat,
    site, branch_id, distribution_channel_code as channel_src,
    customer_id as customer_code, product_id as product_code,
    greatest(try_cast(sold_quantity as double), 0) as qty,
    greatest(try_cast(cost_price as double), 0) as unit_cost,
    greatest(try_cast(net_price as double), 0) as unit_price
  from src
),
vn as (
  select
    order_date,
    order_id_nat,
    site, branch_id,
    map.channel_code,
    customer_code,
    product_code,
    qty, unit_cost, unit_price,
    qty*unit_price as revenue,
    qty*unit_cost as cost,
    (qty*unit_price - qty*unit_cost) as gross_profit
  from clean
  left join {{ ref('seed_channel_map') }} map
    on lower(clean.channel_src) = lower(map.source_value)
)
select * from vn;
```

**stg_payments_vn.sql**
```sql
with src as (select * from {{ source('bronze','payments_raw') }}),
norm as (
  select
    {{ dbt_utils.surrogate_key(['Transaction_ID']) }} as payment_id_nat,
    to_timestamp(Date || ' ' || Time, 'MM/DD/YYYY HH24:MI:SS') at time zone 'Asia/Ho_Chi_Minh' as payment_ts,
    cast(Amount as decimal(18,2)) as amount_src,
    lower(trim(Email)) as email_norm,
    Shipping_Method as shipping_src,
    Payment_Method as method_src,
    Order_Status as status_src,
    Product_Category, Product_Brand
  from src
),
vn as (
  select
    payment_id_nat,
    date(payment_ts) as payment_date,
    m.method_code,
    case when lower(status_src) in ('shipped','delivered','paid','completed') then 'paid'
         when lower(status_src) in ('processing','pending') then 'pending' else 'other' end as status_std,
    amount_src as amount_vnd,
    email_norm, Product_Category, Product_Brand
  from norm n
  left join {{ ref('seed_payment_method_map') }} m
    on lower(n.method_src) = lower(m.source_value)
)
select * from vn;
```

**stg_shipments_vn.sql**
```sql
with src as (select * from {{ source('bronze','shipments_raw') }}),
norm as (
  select
    {{ dbt_utils.surrogate_key(['Transaction_ID','Date']) }} as shipment_id_nat,
    to_timestamp(Date || ' ' || Time, 'MM/DD/YYYY HH24:MI:SS') at time zone 'Asia/Ho_Chi_Minh' as ship_ts,
    lower(trim(Email)) as email_norm,
    Shipping_Method as shipping_src,
    Order_Status as status_src
  from src
),
vn as (
  select
    shipment_id_nat,
    date(ship_ts) as ship_date,
    c.carrier_code, c.service_level,
    case when lower(status_src) in ('delivered','shipped') then 'delivered'
         when lower(status_src) in ('processing','pending') then 'in_transit' else 'other' end as status_std,
    email_norm
  from norm n
  left join {{ ref('seed_carrier_map') }} c
    on lower(n.shipping_src) = lower(c.source_shipping_method)
)
select * from vn;
```

**stg_bank_txn_vn.sql**
```sql
with src as (select * from {{ source('bronze','bank_txn_raw') }}),
norm as (
  select
    booking_id as txn_id_nat,
    cast(bookg_dt_tm_gmt as timestamp) at time zone 'Asia/Ho_Chi_Minh' as txn_ts_local,
    case when bookg_cdt_dbt_ind='CRDT' then bookg_amt_nmrc else -bookg_amt_nmrc end as amount_src,
    acct_ccy as ccy,
    ctpty_nm as counterparty_name,
    end_to_end_id
  from src
),
vn as (
  select
    txn_id_nat,
    date(txn_ts_local) as txn_date,
    (amount_src * coalesce(f.rate_to_vnd, 1)) as amount_vnd,
    case when amount_src >= 0 then 'in' else 'out' end as direction_in_out,
    counterparty_name,
    end_to_end_id
  from norm n
  left join {{ ref('seed_fx_rates') }} f
    on n.ccy = f.ccy
       and n.txn_ts_local::date between f.valid_from and f.valid_to
)
select * from vn;
```

---

## 5) Conformed Dimensions (chuẩn Việt)

**dim_channel.sql**
```sql
{{ config(materialized='incremental', unique_key='channel_code') }}
select distinct
  channel_code,
  initcap(channel_name_vi) as channel_name_vi
from {{ ref('seed_channel_map') }};
```

**dim_payment_method.sql**
```sql
{{ config(materialized='incremental', unique_key='method_code') }}
select distinct
  method_code,
  initcap(method_name_vi) as method_name_vi
from {{ ref('seed_payment_method_map') }};
```

**dim_carrier.sql**
```sql
{{ config(materialized='incremental', unique_key='carrier_code') }}
select distinct
  carrier_code,
  service_level,
  carrier_name_vi
from {{ ref('seed_carrier_map') }};
```

**dim_date.sql** *(có thể build từ spine hoặc từ min/max date trong Silver; include is_holiday_vn qua seed_vn_holidays).*

---

## 6) Facts (tham chiếu dims)

**fact_orders.sql**
```sql
{{ config(materialized='incremental', unique_key='order_id') }}
with s as (select * from {{ ref('stg_orders_vn') }})
select
  s.order_id_nat as order_id,
  cast(to_char(s.order_date, 'YYYYMMDD') as bigint) as date_key,
  dch.channel_code as channel_key,
  s.customer_code as customer_key,
  s.product_code  as product_key,
  s.revenue, s.cost, s.gross_profit, s.qty, s.unit_price, s.unit_cost
from s
left join {{ ref('dim_channel') }} dch on s.channel_code = dch.channel_code;
```

**fact_payments.sql**
```sql
{{ config(materialized='incremental', unique_key='payment_id') }}
with s as (select * from {{ ref('stg_payments_vn') }})
select
  s.payment_id_nat as payment_id,
  cast(to_char(s.payment_date, 'YYYYMMDD') as bigint) as date_key,
  s.email_norm as customer_key,
  dpm.method_code as payment_method_key,
  s.amount_vnd, s.status_std as status
from s
left join {{ ref('dim_payment_method') }} dpm on s.method_code = dpm.method_code;
```

**fact_shipments.sql**
```sql
{{ config(materialized='incremental', unique_key='shipment_id') }}
with s as (select * from {{ ref('stg_shipments_vn') }})
select
  s.shipment_id_nat as shipment_id,
  cast(to_char(s.ship_date, 'YYYYMMDD') as bigint) as date_key_ship,
  dcr.carrier_code as carrier_key,
  s.service_level,
  s.status_std as status
from s
left join {{ ref('dim_carrier') }} dcr on s.carrier_code = dcr.carrier_code;
```

**fact_bank_txn.sql**
```sql
{{ config(materialized='incremental', unique_key='txn_id') }}
with s as (select * from {{ ref('stg_bank_txn_vn') }})
select
  s.txn_id_nat as txn_id,
  cast(to_char(s.txn_date, 'YYYYMMDD') as bigint) as date_key,
  s.amount_vnd,
  s.direction_in_out,
  s.counterparty_name,
  s.end_to_end_id
from s;
```

---

## 7) Link tables (đối soát đa nguồn)

**link_order_payment.sql**
```sql
with o as (
  select
    {{ dbt_utils.surrogate_key(['month_raw','week_raw','site','branch_id','customer_code','product_code']) }} as order_id,
    order_date,
    revenue as order_amount,
    lower(customer_code) as customer_fp
  from {{ ref('stg_orders_vn') }}
),
p as (
  select
    payment_id_nat as payment_id,
    payment_date,
    amount_vnd as pay_amount,
    lower(email_norm) as customer_fp
  from {{ ref('stg_payments_vn') }}
)
select
  o.order_id, p.payment_id,
  case
    when abs(date_diff('day', o.order_date, p.payment_date)) <= 3
     and abs(o.order_amount - p.pay_amount) <= 0.03 * o.order_amount
     and o.customer_fp = p.customer_fp
    then 'cust+time+amount'
    else 'fuzzy'
  end as match_rule,
  case
    when abs(date_diff('day', o.order_date, p.payment_date)) <= 3
     and abs(o.order_amount - p.pay_amount) <= 0.03 * o.order_amount
     and o.customer_fp = p.customer_fp
    then 0.85 else 0.5 end as confidence
from o join p
  on o.customer_fp = p.customer_fp
 and abs(date_diff('day', o.order_date, p.payment_date)) <= 3
 and abs(o.order_amount - p.pay_amount) <= 0.03 * o.order_amount;
```

**link_payment_bank.sql**
```sql
with p as (
  select payment_id_nat as payment_id, payment_date, amount_vnd from {{ ref('stg_payments_vn') }}
),
b as (
  select txn_id_nat as txn_id, txn_date, amount_vnd as bank_amount, direction_in_out
  from {{ ref('stg_bank_txn_vn') }}
)
select
  p.payment_id, b.txn_id,
  case
    when b.direction_in_out='in'
     and abs(date_diff('day', p.payment_date, b.txn_date)) <= 2
     and abs(p.amount_vnd - b.bank_amount) <= 0.02 * p.amount_vnd
    then 'amount+time' else 'fuzzy'
  end as match_rule,
  case
    when b.direction_in_out='in'
     and abs(date_diff('day', p.payment_date, b.txn_date)) <= 2
     and abs(p.amount_vnd - b.bank_amount) <= 0.02 * p.amount_vnd
    then 0.90 else 0.5
  end as confidence
from p join b
  on b.direction_in_out='in'
 and abs(date_diff('day', p.payment_date, b.txn_date)) <= 2
 and abs(p.amount_vnd - b.bank_amount) <= 0.02 * p.amount_vnd;
```

**link_order_shipment.sql**
```sql
with o as (
  select
    {{ dbt_utils.surrogate_key(['month_raw','week_raw','site','branch_id','customer_code','product_code']) }} as order_id,
    order_date,
    lower(customer_code) as customer_fp
  from {{ ref('stg_orders_vn') }}
),
s as (
  select
    shipment_id_nat as shipment_id,
    ship_date,
    lower(email_norm) as customer_fp
  from {{ ref('stg_shipments_vn') }}
)
select
  o.order_id, s.shipment_id,
  case
    when abs(date_diff('day', o.order_date, s.ship_date)) <= 7
     and o.customer_fp = s.customer_fp
    then 'cust+time' else 'fuzzy'
  end as match_rule,
  case
    when abs(date_diff('day', o.order_date, s.ship_date)) <= 7
     and o.customer_fp = s.customer_fp
    then 0.80 else 0.5
  end as confidence
from o join s
  on o.customer_fp = s.customer_fp
 and abs(date_diff('day', o.order_date, s.ship_date)) <= 7;
```

---

## 8) Gold KPIs (ví dụ)

**gold/daily_revenue.sql**
```sql
{{ config(materialized='incremental', unique_key='date_key') }}
select
  cast(to_char(order_date, 'YYYYMMDD') as bigint) as date_key,
  sum(revenue) as total_revenue,
  sum(qty) as total_qty,
  sum(gross_profit) as total_gross_profit
from {{ ref('stg_orders_vn') }}
group by 1
{% if is_incremental() %}
having cast(to_char(max(order_date), 'YYYYMMDD') as bigint)
  > (select coalesce(max(date_key),0) from {{ this }})
{% endif %}
```

**gold/payment_success_rate.sql**
```sql
with op as (
  select distinct order_id from {{ ref('link_order_payment') }}
)
select
  cast(to_char(o.order_date, 'YYYYMMDD') as bigint) as date_key,
  count(distinct o.order_id_nat) as total_orders,
  count(distinct op.order_id) as paid_orders,
  1.0*count(distinct op.order_id)/nullif(count(distinct o.order_id_nat),0) as payment_success_rate
from {{ ref('stg_orders_vn') }} o
left join op on op.order_id = o.order_id_nat
group by 1;
```

---

## 9) Thứ tự chạy (dbt)

1. **Seed**: `dbt deps && dbt seed`  
2. **Silver**: `dbt run --select silver.*`  
3. **Dims**: `dbt run --select dims.*`  
4. **Facts**: `dbt run --select facts.*`  
5. **Links**: `dbt run --select links.*`  
6. **Gold**: `dbt run --select gold.*`  
7. **Tests**: `dbt test`

---

## 10) Data Quality – gợi ý

- Tests: unique/not_null/accepted_values; links có `confidence∈[0,1]`.  
- Great Expectations (tuỳ chọn) cho null/type/range.

---

## 11) Chuẩn hoá “đúng chất Việt” – checklist

- Timezone → `Asia/Ho_Chi_Minh`; Tiền tệ → **VND**.  
- Kênh bán: Online/CHTT/TGPP/BANLE.  
- Payment: cash/card/transfer/vietqr/momo/zalopay/other.  
- Carrier: GHN/GHTK/VTP + service_level.  
- Địa lý: map City/State → province_name_vi.  
- Email/phone chuẩn hoá, số âm → rule xử lý.  

---

## 12) Definition of Done (DoD)

- [ ] `dbt seed` & 4 **Silver** OK  
- [ ] **Dims/Facts** build & tham chiếu chuẩn  
- [ ] **Links** sinh cặp match (`match_rule`,`confidence`)  
- [ ] 2–3 **Gold KPI** chạy OK  
- [ ] `dbt test` pass (unique/not_null/accepted_values)  
- [ ] README/Logic mapping rõ ràng

---

## 13) Troubleshooting

- Sai join seeds → kiểm tra `lower/trim`.  
- Lệch VND/Timezone → kiểm tra seed_fx & `at time zone`.  
- Link ít → nới window ngày/tolerance %, thêm signal (brand/category).  
- Hiệu năng → incremental + partition theo date.
