-- PostgreSQL Initialization Script for CryptoUpdate
-- This script sets up the initial database structure

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_crypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS crypto;
CREATE SCHEMA IF NOT EXISTS portfolio;
CREATE SCHEMA IF NOT EXISTS market;
CREATE SCHEMA IF NOT EXISTS operations;

-- Set search path
ALTER DATABASE cryptoupdate SET search_path TO crypto, portfolio, market, operations, public;

-- Create basic tables structure (migrate from SQLite schema)

-- Portfolios table
CREATE TABLE IF NOT EXISTS portfolio.portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Tokens/Assets table
CREATE TABLE IF NOT EXISTS crypto.tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    contract_address VARCHAR(255),
    decimals INTEGER DEFAULT 18,
    chain VARCHAR(100) DEFAULT 'ethereum',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Market data table
CREATE TABLE IF NOT EXISTS market.prices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id UUID REFERENCES crypto.tokens(id),
    price DECIMAL(20, 8) NOT NULL,
    volume_24h DECIMAL(20, 8),
    market_cap DECIMAL(20, 2),
    price_change_24h DECIMAL(10, 4),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(100) DEFAULT 'api',
    CONSTRAINT unique_token_timestamp UNIQUE(token_id, timestamp)
);

-- Operations/Transactions table
CREATE TABLE IF NOT EXISTS operations.transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID REFERENCES portfolio.portfolios(id),
    token_id UUID REFERENCES crypto.tokens(id),
    transaction_type VARCHAR(50) NOT NULL, -- 'buy', 'sell', 'transfer', 'stake', etc.
    quantity DECIMAL(30, 18) NOT NULL,
    price DECIMAL(20, 8),
    fee DECIMAL(20, 8) DEFAULT 0,
    transaction_hash VARCHAR(255),
    block_number BIGINT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Portfolio holdings (current balances)
CREATE TABLE IF NOT EXISTS portfolio.holdings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID REFERENCES portfolio.portfolios(id),
    token_id UUID REFERENCES crypto.tokens(id),
    quantity DECIMAL(30, 18) NOT NULL DEFAULT 0,
    average_cost DECIMAL(20, 8),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_portfolio_token UNIQUE(portfolio_id, token_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_prices_token_timestamp ON market.prices(token_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_portfolio ON operations.transactions(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_transactions_token ON operations.transactions(token_id);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON operations.transactions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON portfolio.holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_tokens_symbol ON crypto.tokens(symbol);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER set_timestamp_portfolios
    BEFORE UPDATE ON portfolio.portfolios
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_set_timestamp();

CREATE TRIGGER set_timestamp_tokens
    BEFORE UPDATE ON crypto.tokens
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_set_timestamp();

-- Insert some sample data
INSERT INTO crypto.tokens (symbol, name) VALUES 
    ('BTC', 'Bitcoin'),
    ('ETH', 'Ethereum'),
    ('USDT', 'Tether'),
    ('USDC', 'USD Coin')
ON CONFLICT (symbol) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA crypto TO crypto_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA portfolio TO crypto_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA market TO crypto_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA operations TO crypto_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA crypto TO crypto_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA portfolio TO crypto_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA market TO crypto_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA operations TO crypto_user;