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
    CASE
      WHEN b.direction_in_out = 'in' AND LOWER(b.counterparty_name) LIKE '%customer%' THEN 'RECEIVABLE'
      WHEN b.direction_in_out = 'in' THEN 'OTHER_INCOME'
      WHEN b.direction_in_out = 'out' AND LOWER(b.counterparty_name) LIKE '%supplier%' THEN 'PAYABLE'
      WHEN b.direction_in_out = 'out' AND LOWER(b.counterparty_name) LIKE '%salary%' THEN 'PAYROLL'
      WHEN b.direction_in_out = 'out' THEN 'OTHER_EXPENSE'
      ELSE 'UNCLASSIFIED'
    END AS transaction_category,
    
    -- Audit
    b.stg_loaded_at AS source_loaded_at,
    CURRENT_TIMESTAMP AS created_at
    
  FROM {{ ref('stg_bank_txn_vn') }} b
)

SELECT * FROM bank_txn_enriched
