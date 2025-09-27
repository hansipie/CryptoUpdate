-- Migration script to help migrate data from SQLite to PostgreSQL
-- This script creates views and functions to ease the migration process

-- Create a function to migrate SQLite data (to be called manually)
CREATE OR REPLACE FUNCTION migrate_sqlite_data()
RETURNS TEXT AS $$
DECLARE
    result_msg TEXT;
BEGIN
    -- This function serves as a template for manual data migration
    -- You'll need to export data from SQLite and import it here
    
    -- Example migration steps:
    -- 1. Export SQLite data to CSV files
    -- 2. Use COPY commands to import the data
    -- 3. Transform data types as needed
    
    result_msg := 'Migration template created. Manual steps required:
    
    1. Export SQLite tables to CSV:
       sqlite3 data/db.sqlite3 ".mode csv" ".output portfolios.csv" "SELECT * FROM portfolios;"
       
    2. Import to PostgreSQL:
       COPY portfolio.portfolios(name, description, created_at) 
       FROM ''/path/to/portfolios.csv'' 
       WITH (FORMAT csv, HEADER true);
       
    3. Repeat for all tables with appropriate column mappings';
    
    RETURN result_msg;
END;
$$ LANGUAGE plpgsql;

-- Create views for data validation after migration
CREATE OR REPLACE VIEW migration.validation_summary AS
SELECT 
    'portfolios' as table_name,
    COUNT(*) as record_count
FROM portfolio.portfolios
UNION ALL
SELECT 
    'tokens' as table_name,
    COUNT(*) as record_count
FROM crypto.tokens
UNION ALL
SELECT 
    'transactions' as table_name,
    COUNT(*) as record_count
FROM operations.transactions
UNION ALL
SELECT 
    'holdings' as table_name,
    COUNT(*) as record_count
FROM portfolio.holdings;

-- Create a function to update holdings based on transactions
CREATE OR REPLACE FUNCTION update_portfolio_holdings()
RETURNS VOID AS $$
BEGIN
    -- Recalculate holdings based on transactions
    WITH transaction_summary AS (
        SELECT 
            portfolio_id,
            token_id,
            SUM(CASE 
                WHEN transaction_type IN ('buy', 'deposit', 'stake_reward') THEN quantity
                WHEN transaction_type IN ('sell', 'withdraw', 'fee') THEN -quantity
                ELSE 0
            END) as total_quantity,
            AVG(CASE 
                WHEN transaction_type IN ('buy', 'deposit') AND price > 0 THEN price
                ELSE NULL
            END) as avg_price
        FROM operations.transactions
        GROUP BY portfolio_id, token_id
    )
    INSERT INTO portfolio.holdings (portfolio_id, token_id, quantity, average_cost)
    SELECT 
        portfolio_id,
        token_id,
        total_quantity,
        avg_price
    FROM transaction_summary
    WHERE total_quantity > 0
    ON CONFLICT (portfolio_id, token_id) 
    DO UPDATE SET 
        quantity = EXCLUDED.quantity,
        average_cost = EXCLUDED.average_cost,
        last_updated = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;