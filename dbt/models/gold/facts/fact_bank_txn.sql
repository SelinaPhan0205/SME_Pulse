{{ config(
    materialized = 'table',
    tags = ['gold', 'fact', 'bank', 'cashflow']
) }}

-- =====================================================================
-- 🏦 FACT_BANK_TXN: Bank transactions (cash flow monitoring)
-- Purpose: Bank account transactions for cash flow analysis
-- Grain: 1 row = 1 bank transaction
-- =====================================================================

WITH bank_txn_enriched AS (
  SELECT
    -- Natural Key
    b.txn_id_nat AS txn_id,
    
    -- Date dimension FK
    CAST(date_format(b.txn_date, '%Y%m%d') AS BIGINT) AS date_key,
    b.txn_date,
    b.txn_ts_local AS txn_timestamp,
    
    -- Degenerate dimensions
    b.ccy AS currency_code,
    b.direction_in_out,
    b.counterparty_name,
    b.end_to_end_id,
    
    -- Measures (additive)
    b.amount_src AS amount_original,
    b.amount_vnd,
    
    -- Derived measures
    CASE 
      WHEN b.direction_in_out = 'in' THEN b.amount_vnd ELSE 0 
    END AS cash_inflow_vnd,
    
    CASE 
      WHEN b.direction_in_out = 'out' THEN ABS(b.amount_vnd) ELSE 0 
    END AS cash_outflow_vnd,
    
    -- Flags
    CASE WHEN b.direction_in_out = 'in' THEN TRUE ELSE FALSE END AS is_inflow,
    CASE WHEN ABS(b.amount_vnd) > 100000000 THEN TRUE ELSE FALSE END AS is_large_transaction,  -- >100M VND
    
    -- Transaction classification (for cash flow forecasting)
    -- FIX [P1]: Keyword-based classification for Vietnamese bank counterparty names
    CASE
      -- Receivables: customer payments, sales revenue
      WHEN b.direction_in_out = 'in' AND (
        LOWER(b.counterparty_name) LIKE '%customer%'
        OR LOWER(b.counterparty_name) LIKE '%khach%'
        OR LOWER(b.counterparty_name) LIKE '%kh %'
        OR LOWER(b.counterparty_name) LIKE '%doanh thu%'
        OR LOWER(b.counterparty_name) LIKE '%ban hang%'
        OR LOWER(b.counterparty_name) LIKE '%thu tien%'
        OR LOWER(b.counterparty_name) LIKE '%thanh toan%'
        OR LOWER(b.counterparty_name) LIKE '%cong ty%'
        OR LOWER(b.counterparty_name) LIKE '%payment%'
        OR LOWER(b.counterparty_name) LIKE '%invoice%'
      ) THEN 'RECEIVABLE'

      -- Other income (inflows not matching receivables)
      WHEN b.direction_in_out = 'in' THEN 'OTHER_INCOME'

      -- Payables: supplier payments, material/goods purchases
      WHEN b.direction_in_out = 'out' AND (
        LOWER(b.counterparty_name) LIKE '%supplier%'
        OR LOWER(b.counterparty_name) LIKE '%nha cung%'
        OR LOWER(b.counterparty_name) LIKE '%ncc%'
        OR LOWER(b.counterparty_name) LIKE '%mua hang%'
        OR LOWER(b.counterparty_name) LIKE '%nguyen lieu%'
        OR LOWER(b.counterparty_name) LIKE '%vat tu%'
        OR LOWER(b.counterparty_name) LIKE '%vendor%'
        OR LOWER(b.counterparty_name) LIKE '%purchase%'
      ) THEN 'PAYABLE'

      -- Payroll: salary, wages, bonus
      WHEN b.direction_in_out = 'out' AND (
        LOWER(b.counterparty_name) LIKE '%salary%'
        OR LOWER(b.counterparty_name) LIKE '%luong%'
        OR LOWER(b.counterparty_name) LIKE '%thuong%'
        OR LOWER(b.counterparty_name) LIKE '%nhan vien%'
        OR LOWER(b.counterparty_name) LIKE '%payroll%'
        OR LOWER(b.counterparty_name) LIKE '%wage%'
      ) THEN 'PAYROLL'

      -- Tax / Government
      WHEN b.direction_in_out = 'out' AND (
        LOWER(b.counterparty_name) LIKE '%thue%'
        OR LOWER(b.counterparty_name) LIKE '%tax%'
        OR LOWER(b.counterparty_name) LIKE '%bao hiem%'
        OR LOWER(b.counterparty_name) LIKE '%bhxh%'
      ) THEN 'TAX_INSURANCE'

      -- Utilities / Rent
      WHEN b.direction_in_out = 'out' AND (
        LOWER(b.counterparty_name) LIKE '%dien%'
        OR LOWER(b.counterparty_name) LIKE '%nuoc%'
        OR LOWER(b.counterparty_name) LIKE '%thue mat bang%'
        OR LOWER(b.counterparty_name) LIKE '%rent%'
        OR LOWER(b.counterparty_name) LIKE '%utility%'
      ) THEN 'UTILITIES_RENT'

      -- Other expenses (outflows not matching above)
      WHEN b.direction_in_out = 'out' THEN 'OTHER_EXPENSE'

      ELSE 'UNCLASSIFIED'
    END AS transaction_category,
    
    -- Audit
    b.stg_loaded_at AS source_loaded_at,
    CURRENT_TIMESTAMP AS created_at
    
  FROM {{ ref('stg_bank_txn_vn') }} b
)

SELECT * FROM bank_txn_enriched


