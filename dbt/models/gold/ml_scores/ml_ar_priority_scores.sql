{{ config(
    materialized='table',
    tags=['gold', 'ml_scores', 'ar_priority', 'uc05']
) }}

-- ===================================================================
-- ML_AR_PRIORITY_SCORES: Điểm ưu tiên thu nợ (Heuristic scoring)
-- Thuật toán rule-based tính điểm từ 3 components:
-- - Overdue score (0-40): Dựa trên days_overdue
-- - Amount score (0-30): Dựa trên invoice_amount_vnd
-- - Risk score (0-30): Dựa trên customer behavior
-- ===================================================================

WITH scoring_data AS (
    SELECT 
        invoice_id,
        cust_number as customer_id,
        total_open_amount as invoice_amount_vnd,
        
        -- Calculate days_overdue (approximate from flags)
        CASE 
            WHEN is_overdue_60 = 1 THEN 75
            WHEN is_overdue_30 = 1 THEN 45
            ELSE 0
        END as days_overdue,
        
        -- Customer features
        coalesce(cust_recency_days, -1) as cust_recency_days,
        coalesce(cust_frequency_ltm, 0) as cust_frequency_ltm,
        customer_segment
        
    FROM {{ ref('ml_training_ar_scoring') }}
    WHERE total_open_amount > 0
),

scored AS (
    SELECT 
        invoice_id,
        customer_id,
        invoice_amount_vnd,
        days_overdue,
        
        -- Component 1: Overdue Score (0-40)
        CASE 
            WHEN days_overdue = 0 THEN 0
            WHEN days_overdue <= 30 THEN 10
            WHEN days_overdue <= 60 THEN 20
            WHEN days_overdue <= 90 THEN 30
            ELSE 40
        END as overdue_score,
        
        -- Component 2: Amount Score (0-30)
        CASE 
            WHEN invoice_amount_vnd >= 10000000 THEN 30
            WHEN invoice_amount_vnd >= 5000000 THEN 20
            WHEN invoice_amount_vnd >= 1000000 THEN 10
            ELSE 5
        END as amount_score,
        
        -- Component 3: Risk Score (0-30)
        (
            -- Customer segment (0-15)
            CASE 
                WHEN customer_segment = 'Inactive' THEN 15
                WHEN customer_segment = 'Regular' THEN 5
                WHEN customer_segment = 'High Value' THEN 2
                ELSE 0
            END +
            
            -- Recency (0-10)
            CASE 
                WHEN cust_recency_days > 180 THEN 10
                WHEN cust_recency_days > 90 THEN 5
                WHEN cust_recency_days > 30 THEN 2
                ELSE 0
            END +
            
            -- Frequency (0-5)
            CASE 
                WHEN cust_frequency_ltm = 0 THEN 5
                WHEN cust_frequency_ltm < 3 THEN 3
                ELSE 0
            END
        ) as risk_score
        
    FROM scoring_data
),

final_scores AS (
    SELECT 
        invoice_id,
        customer_id,
        invoice_amount_vnd,
        days_overdue,
        overdue_score,
        amount_score,
        risk_score,
        
        -- Total priority score
        (overdue_score + amount_score + risk_score) as priority_score,
        
        -- Priority tier
        CASE 
            WHEN (overdue_score + amount_score + risk_score) >= 70 THEN 'URGENT'
            WHEN (overdue_score + amount_score + risk_score) >= 50 THEN 'HIGH'
            WHEN (overdue_score + amount_score + risk_score) >= 30 THEN 'MEDIUM'
            ELSE 'LOW'
        END as priority_tier,
        
        -- Priority rank
        DENSE_RANK() OVER (ORDER BY (overdue_score + amount_score + risk_score) DESC) as priority_rank,
        
        CURRENT_TIMESTAMP as scored_at
        
    FROM scored
)

SELECT * FROM final_scores


