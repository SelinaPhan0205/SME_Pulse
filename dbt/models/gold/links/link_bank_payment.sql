{{ config(
  materialized = 'table',
    tags = ['gold', 'link', 'reconciliation', 'cashflow']
) }}

-- =====================================================================
-- 🔗 LINK_BANK_PAYMENT: Bank transactions ↔ Payments reconciliation
-- Purpose: Match bank inflows to retail payments for cash flow tracking
-- Grain: 1 row = 1 bank-payment match (bijective: 1 bank ↔ 1 payment)
-- Fixes applied:
--   [P0] Removed 1% sampling (MOD hack)
--   [P0] Fixed date_key arithmetic → proper DATE functions
--   [P1] Replaced hardcoded customer_match_score with actual logic
--   [P1] Enforced bijective matching (1:1) to prevent double-counting
-- =====================================================================

WITH bank_inflows AS (
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
    {% if is_incremental() %}
    AND txn_date >= (SELECT COALESCE(MAX(bank_date), DATE '2020-01-01') FROM {{ this }}) - INTERVAL '7' DAY
    {% endif %}
),

successful_payments AS (
  SELECT
    payment_id,
    date_key,
    payment_date,
    total_amount_vnd,
    customer_email,
    is_successful_payment
  FROM {{ ref('fact_payments') }}
  WHERE is_successful_payment = TRUE
    {% if is_incremental() %}
    AND payment_date >= (SELECT COALESCE(MAX(payment_date), DATE '2020-01-01') FROM {{ this }}) - INTERVAL '7' DAY
    {% endif %}
),

-- Fuzzy matching: amount + date proximity
-- FIX: Use proper DATE arithmetic instead of integer date_key ±7
fuzzy_matches AS (
  SELECT
    b.txn_id AS bank_txn_id,
    b.txn_date AS bank_date,
    b.amount_vnd AS bank_amount_vnd,
    b.counterparty_name,

    p.payment_id,
    p.payment_date,
    p.total_amount_vnd AS payment_amount_vnd,
    p.customer_email,

    -- 1. Amount match score (max 40 points)
    ABS(b.amount_vnd - p.total_amount_vnd) AS amount_variance_vnd,
    CASE
      WHEN ABS(b.amount_vnd - p.total_amount_vnd) <= 100000 THEN 40
      WHEN ABS(b.amount_vnd - p.total_amount_vnd) / NULLIF(b.amount_vnd, 0) <= 0.01 THEN 30
      WHEN ABS(b.amount_vnd - p.total_amount_vnd) / NULLIF(b.amount_vnd, 0) <= 0.05 THEN 10
      ELSE 0
    END AS amount_match_score,

    -- 2. Date proximity score (max 40 points)
    ABS(DATE_DIFF('day', b.txn_date, p.payment_date)) AS date_diff_days,
    CASE
      WHEN DATE_DIFF('day', b.txn_date, p.payment_date) = 0 THEN 40
      WHEN ABS(DATE_DIFF('day', b.txn_date, p.payment_date)) <= 1 THEN 30
      WHEN ABS(DATE_DIFF('day', b.txn_date, p.payment_date)) <= 3 THEN 20
      WHEN ABS(DATE_DIFF('day', b.txn_date, p.payment_date)) <= 7 THEN 10
      ELSE 0
    END AS date_match_score,

    -- 3. Customer name matching (max 20 points)
    -- FIX: Replace hardcoded 20 with actual counterparty comparison
    CASE
      WHEN b.counterparty_name IS NOT NULL
        AND p.customer_email IS NOT NULL
        AND LOWER(b.counterparty_name) = LOWER(SPLIT_PART(p.customer_email, '@', 1))
        THEN 20
      WHEN b.counterparty_name IS NOT NULL
        AND p.customer_email IS NOT NULL
        AND STRPOS(LOWER(b.counterparty_name), LOWER(SPLIT_PART(p.customer_email, '@', 1))) > 0
        THEN 10
      ELSE 0
    END AS customer_match_score,

    CURRENT_TIMESTAMP AS created_at

  FROM bank_inflows b
  INNER JOIN successful_payments p
    -- FIX: Use proper DATE arithmetic instead of date_key ±7
    ON p.payment_date BETWEEN DATE_ADD('day', -7, b.txn_date)
                          AND DATE_ADD('day',  7, b.txn_date)
  WHERE
    -- Pre-filter: amount within 10%
    ABS(b.amount_vnd - p.total_amount_vnd) / NULLIF(b.amount_vnd, 0) <= 0.10
),

scored_matches AS (
  SELECT
    *,
    amount_match_score + date_match_score + customer_match_score AS total_match_score,
    CASE
      WHEN amount_match_score + date_match_score + customer_match_score >= 80 THEN 'HIGH'
      WHEN amount_match_score + date_match_score + customer_match_score >= 50 THEN 'MEDIUM'
      WHEN amount_match_score + date_match_score + customer_match_score >= 30 THEN 'LOW'
      ELSE 'VERY_LOW'
    END AS match_confidence,

    -- Best match per bank transaction (bijective: 1 bank → 1 payment)
    ROW_NUMBER() OVER (
      PARTITION BY bank_txn_id
      ORDER BY (amount_match_score + date_match_score + customer_match_score) DESC,
               amount_variance_vnd ASC,
               date_diff_days ASC
    ) AS rank_per_bank,

    -- Best match per payment (bijective: 1 payment → 1 bank)
    ROW_NUMBER() OVER (
      PARTITION BY payment_id
      ORDER BY (amount_match_score + date_match_score + customer_match_score) DESC,
               amount_variance_vnd ASC,
               date_diff_days ASC
    ) AS rank_per_payment

  FROM fuzzy_matches
),

-- FIX: Enforce bijective matching — only keep pairs where BOTH sides are best match
-- This prevents double-counting (1 payment matched to multiple bank txns or vice versa)
bijective_matches AS (
  SELECT *
  FROM scored_matches
  WHERE rank_per_bank = 1 AND rank_per_payment = 1
    AND total_match_score >= 30
),

-- Also track unmatched bank transactions for manual review
unmatched_bank AS (
  SELECT
    b.txn_id AS bank_txn_id,
    b.txn_date AS bank_date,
    b.amount_vnd AS bank_amount_vnd,
    CAST(NULL AS VARCHAR) AS payment_id,
    CAST(NULL AS DATE) AS payment_date,
    CAST(NULL AS DOUBLE) AS payment_amount_vnd,
    CAST(NULL AS DOUBLE) AS amount_variance_vnd,
    CAST(NULL AS BIGINT) AS date_diff_days,
    0 AS amount_match_score,
    0 AS date_match_score,
    0 AS customer_match_score,
    0 AS total_match_score,
    'UNMATCHED' AS match_confidence,
    TRUE AS is_best_match,
    'PENDING_REVIEW' AS match_method,
    CURRENT_TIMESTAMP AS created_at
  FROM bank_inflows b
  WHERE b.txn_id NOT IN (SELECT bank_txn_id FROM bijective_matches)
)

SELECT
  CAST(COALESCE(CAST(bank_txn_id AS VARCHAR), '') || '_' || COALESCE(CAST(payment_id AS VARCHAR), 'unmatched') AS VARCHAR) AS match_key,
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
  TRUE AS is_best_match,
  'MATCHED' AS match_method,
  created_at
FROM bijective_matches

UNION ALL

SELECT
  CAST(CAST(bank_txn_id AS VARCHAR) || '_unmatched' AS VARCHAR) AS match_key,
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
  is_best_match,
  match_method,
  created_at
FROM unmatched_bank

ORDER BY bank_txn_id, total_match_score DESC

