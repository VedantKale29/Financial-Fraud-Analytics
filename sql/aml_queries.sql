-- ===============================
-- High value transactions
-- ===============================

SELECT *
FROM fact_transactions
WHERE amount > 10000;



-- ===============================
-- Fraud transactions
-- ===============================

SELECT *
FROM fact_transactions
WHERE is_fraud = TRUE;



-- ===============================
-- Fraud by customer
-- ===============================

SELECT
    customer_id,
    COUNT(*) AS fraud_count
FROM fact_transactions
WHERE is_fraud = TRUE
GROUP BY customer_id
ORDER BY fraud_count DESC;



-- ===============================
-- Risk segment analysis
-- ===============================

SELECT
    c.risk_segment,
    COUNT(*) AS total_txn,
    SUM(f.amount) AS total_amount

FROM fact_transactions f
JOIN dim_customers c
ON f.customer_id = c.customer_id

GROUP BY c.risk_segment;



-- ===============================
-- Weekend fraud detection
-- ===============================

SELECT
    d.day_of_week,
    COUNT(*) AS fraud_txn

FROM fact_transactions f
JOIN dim_date d
ON f.date_key = d.date_key

WHERE f.is_fraud = TRUE

GROUP BY d.day_of_week;