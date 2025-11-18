{{ config(
    materialized = 'table',
    tags = ['gold', 'link', 'reconciliation', 'cashflow']
) }}

-- =====================================================================
-- 🔗 LINK_BANK_PAYMENT: Bank transactions ↔ Payments reconciliation
-- Purpose: Match bank inflows to retail payments for cash flow tracking
-- Grain: 1 row = 1 bank-payment match (many-to-many possible)
-- =====================================================================

WITH bank_inflows AS (
  -- Chỉ lấy bank transactions là INFLOW
  SELECT
    txn_id,
    date_key,
    txn_date,
    amount_vnd,
    counterparty_name,
    is_inflow,
    transaction_category
  FROM {{ ref('fact_bank_txn') }}
  WHERE is_inflow = TRUE
    AND transaction_category IN ('RECEIVABLE', 'OTHER_INCOME')
    AND MOD(date_key, 100) = 0  -- SAMPLE 1% for testing
),

successful_payments AS (
  -- Chỉ lấy payments đã PAID thành công
  SELECT
    payment_id,
    date_key,
    payment_date,
    total_amount_vnd,
    customer_email,
    is_successful_payment
  FROM {{ ref('fact_payments') }}
  WHERE is_successful_payment = TRUE
    AND MOD(date_key, 100) = 0  -- SAMPLE 1% for testing
),

-- Fuzzy matching: amount + date proximity
-- Use date_key join to avoid CROSS JOIN memory explosion
fuzzy_matches AS (
  SELECT
    b.txn_id AS bank_txn_id,
    b.txn_date AS bank_date,
    b.amount_vnd AS bank_amount_vnd,
    
    p.payment_id,
    p.payment_date,
    p.total_amount_vnd AS payment_amount_vnd,
    
    -- Match score components
    -- 1. Amount variance (tối đa 1% hoặc 100K VND)
    ABS(b.amount_vnd - p.total_amount_vnd) AS amount_variance_vnd,
    CASE 
      WHEN ABS(b.amount_vnd - p.total_amount_vnd) <= 100000 THEN 40  -- Perfect match
      WHEN ABS(b.amount_vnd - p.total_amount_vnd) / NULLIF(b.amount_vnd, 0) <= 0.01 THEN 30  -- 1% tolerance
      WHEN ABS(b.amount_vnd - p.total_amount_vnd) / NULLIF(b.amount_vnd, 0) <= 0.05 THEN 10  -- 5% tolerance
      ELSE 0
    END AS amount_match_score,
    
    -- 2. Date proximity (same day = 40 points, within 3 days = 20 points)
    ABS(DATE_DIFF('day', b.txn_date, p.payment_date)) AS date_diff_days,
    CASE 
      WHEN DATE_DIFF('day', b.txn_date, p.payment_date) = 0 THEN 40  -- Same day
      WHEN ABS(DATE_DIFF('day', b.txn_date, p.payment_date)) <= 1 THEN 30  -- Next day
      WHEN ABS(DATE_DIFF('day', b.txn_date, p.payment_date)) <= 3 THEN 20  -- Within 3 days
      WHEN ABS(DATE_DIFF('day', b.txn_date, p.payment_date)) <= 7 THEN 10  -- Within 1 week
      ELSE 0
    END AS date_match_score,
    
    -- 3. Customer name matching (if available) - placeholder
    20 AS customer_match_score,  -- Future: LEVENSHTEIN distance on counterparty vs customer
    
    CURRENT_TIMESTAMP AS created_at
    
  FROM bank_inflows b
  INNER JOIN successful_payments p
    -- Join on date_key ±7 days to reduce cartesian product
    ON p.date_key BETWEEN b.date_key - 7 AND b.date_key + 7
  WHERE 
    -- Pre-filter: amount within 10%
    ABS(b.amount_vnd - p.total_amount_vnd) / NULLIF(b.amount_vnd, 0) <= 0.10
),

-- Calculate total match score
scored_matches AS (
  SELECT
    *,
    amount_match_score + date_match_score + customer_match_score AS total_match_score,
    
    -- Match confidence level
    CASE 
      WHEN amount_match_score + date_match_score + customer_match_score >= 80 THEN 'HIGH'
      WHEN amount_match_score + date_match_score + customer_match_score >= 50 THEN 'MEDIUM'
      WHEN amount_match_score + date_match_score + customer_match_score >= 30 THEN 'LOW'
      ELSE 'VERY_LOW'
    END AS match_confidence,
    
    -- Best match flag (per bank transaction, highest score)
    ROW_NUMBER() OVER (
      PARTITION BY bank_txn_id 
      ORDER BY (amount_match_score + date_match_score + customer_match_score) DESC
    ) AS match_rank
    
  FROM fuzzy_matches
)

-- Return all matches with score >= 30 (threshold for consideration)
SELECT 
  bank_txn_id,
  bank_date,
  bank_amount_vnd,
  payment_id,
  payment_date,
  payment_amount_vnd,
  amount_variance_vnd,
  date_diff_days,
  amount_match_score,
  date_match_score,
  customer_match_score,
  total_match_score,
  match_confidence,
  CASE WHEN match_rank = 1 THEN TRUE ELSE FALSE END AS is_best_match,
  created_at
FROM scored_matches
WHERE total_match_score >= 30  -- Threshold: only keep reasonable matches
ORDER BY bank_txn_id, total_match_score DESC

