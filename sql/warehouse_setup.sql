-- ===============================
-- DIMENSION TABLES
-- ===============================

CREATE TABLE dim_customers (
    customer_id INT PRIMARY KEY,
    name TEXT,
    kyc_status TEXT,
    risk_segment TEXT
);


CREATE TABLE dim_accounts (
    account_id INT PRIMARY KEY,
    customer_id INT,
    account_type TEXT,
    balance_limit FLOAT
);


CREATE TABLE dim_date (
    date_key INT PRIMARY KEY,
    full_date DATE,
    day_of_week TEXT,
    is_weekend BOOLEAN
);



-- ===============================
-- FACT TABLE
-- ===============================

CREATE TABLE fact_transactions (

    transaction_id INT PRIMARY KEY,

    customer_id INT,
    account_id INT,
    date_key INT,

    amount FLOAT,
    is_fraud BOOLEAN,

    FOREIGN KEY (customer_id)
        REFERENCES dim_customers(customer_id),

    FOREIGN KEY (account_id)
        REFERENCES dim_accounts(account_id),

    FOREIGN KEY (date_key)
        REFERENCES dim_date(date_key)

);