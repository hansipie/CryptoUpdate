# Project-Specific Instructions

## Technology Stack

**Core Technologies:**
- **Language**: Python 3.x
- **Dependency Management**: uv (ultra-fast Python package manager)
- **Web Framework**: Streamlit (for interactive web applications)
- **Containerization**: Docker
- **Environment**: Container-based deployment

## Development Environment Setup

### Local Development

**Using uv for dependency management:**

```bash
# Install dependencies
uv sync

# Add new dependency
uv add package-name

# Add development dependency
uv add --dev package-name

# Update dependencies
uv lock --upgrade

# Run Python with uv environment
uv run python script.py

# Activate virtual environment
uv venv --activate
```

### Streamlit Development

**Running the web application:**

```bash
# Run Streamlit app locally
uv run streamlit run app.py
```

### Docker Development

**Container operations:**

```bash
# Build and run with docker compose
docker compose up

# Port mapping: 8042:8080 (host:container)
# Access application at: http://localhost:8042
# Note: Container runs Streamlit on port 8080, mapped to host port 8042

# Development mode with live reload
docker compose up --watch
```

**Volume mounts:**
- `./archives` → Container archives directory
- `./data` → Container data directory (persists database)

**Container details:**
- User: docker (UID 1000, GID 1000)
- Base image: python:3-slim
- Command: `uv run streamlit run app.py --server.port 8080`

## Project Structure

**Key directories and files:**
- `app_pages/`: Streamlit application pages
- `tests/`: Test files
- `Dockerfile`: Container configuration
- `pyproject.toml`: Python project configuration and dependencies
- `uv.lock`: Locked dependency versions

## Code Quality Standards

### Python Code Style

**Follow these conventions:**
- Use Python PEP 8 style guidelines
- Use type hints for function parameters and return values
- Use docstrings for modules, classes, and functions
- Keep functions small and focused
- Use meaningful variable and function names

**Example:**
```python
from typing import Dict, List, Optional
import streamlit as st

def calculate_portfolio_performance(
    holdings: Dict[str, float],
    prices: Dict[str, float]
) -> Optional[float]:
    """Calculate total portfolio performance.
    
    Args:
        holdings: Dictionary of asset symbols to quantities
        prices: Dictionary of asset symbols to current prices
    
    Returns:
        Total portfolio value or None if calculation fails
    """
    try:
        total_value = sum(
            holdings.get(symbol, 0) * prices.get(symbol, 0)
            for symbol in holdings
        )
        return total_value
    except Exception as e:
        st.error(f"Portfolio calculation failed: {e}")
        return None
```

### Streamlit Best Practices

**UI/UX Guidelines:**
- Use `st.cache_data` for expensive computations
- Use `st.session_state` for maintaining state across reruns
- Organize code with clear page structure
- Use columns and containers for layout
- Handle errors gracefully with user-friendly messages

**Example:**
```python
import streamlit as st
import pandas as pd

@st.cache_data
def load_crypto_data(symbol: str) -> pd.DataFrame:
    """Load and cache cryptocurrency data."""
    # Implementation here
    pass

# Page configuration
st.set_page_config(
    page_title="Crypto Portfolio",
    page_icon="₿",
    layout="wide"
)

# Main application logic
col1, col2 = st.columns(2)
with col1:
    st.header("Portfolio Overview")
    # Content here

with col2:
    st.header("Performance Metrics")
    # Content here
```

## Testing Standards

### Test Structure

**Test organization:**
- Unit tests for core business logic
- Integration tests for external API calls
- Streamlit app tests for UI components

**Example test structure:**
```python
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

def test_calculate_portfolio_performance():
    """Test portfolio performance calculation."""
    holdings = {"BTC": 1.0, "ETH": 2.0}
    prices = {"BTC": 50000, "ETH": 3000}
    
    result = calculate_portfolio_performance(holdings, prices)
    
    assert result == 56000

@pytest.fixture
def sample_crypto_data():
    """Fixture providing sample cryptocurrency data."""
    return pd.DataFrame({
        'symbol': ['BTC', 'ETH'],
        'price': [50000, 3000],
        'volume': [1000000, 500000]
    })
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=.

# Run specific test file
uv run pytest tests/test_portfolio.py

# Run tests in Docker
docker run crypto-update uv run pytest
```

## Deployment

### Docker Deployment

**Dockerfile best practices:**
- Use multi-stage builds for smaller images
- Copy only necessary files
- Set appropriate user permissions
- Expose correct ports (8501 for Streamlit)

**Environment variables:**
- Use `.env` files for local development
- Use Docker environment variables for production
- Never commit secrets or API keys

### Production Considerations

**Before deployment:**
- [ ] All tests pass
- [ ] Dependencies are locked with `uv.lock`
- [ ] Docker image builds successfully
- [ ] Environment variables configured
- [ ] Health checks implemented
- [ ] Logging configured appropriately

## Development Commands

**Common development tasks:**

```bash
# Development setup
uv sync
uv run streamlit run app.py

# Testing
uv run pytest
uv run pytest --cov=.

# Code quality
uv run ruff check .
uv run ruff format .
uv run mypy .

# Docker operations
docker compose up

# Dependency management
uv add requests
uv add --dev pytest
uv lock --upgrade
```

## Security Guidelines

**Data Security:**
- Never log or display API keys
- Use environment variables for sensitive configuration
- Validate all user inputs
- Use HTTPS in production
- Implement rate limiting for API calls

**Streamlit Security:**
- Use `st.secrets` for sensitive configuration in Streamlit Cloud
- Validate file uploads if accepting user files
- Sanitize user inputs before processing
- Use authentication if handling sensitive data

## Performance Optimization

**Streamlit Performance:**
- Use `@st.cache_data` for expensive operations
- Minimize API calls with caching
- Use `st.empty()` for dynamic content updates
- Optimize DataFrame operations with pandas

**Docker Performance:**
- Use appropriate base images (python:3.x-slim)
- Multi-stage builds to reduce image size
- Proper layer caching in Dockerfile
- Health checks for container monitoring

## Error Handling

**Application Error Handling:**
```python
import streamlit as st
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Risky operation
    result = fetch_crypto_data(symbol)
except APIError as e:
    logger.error(f"API error: {e}")
    st.error("Unable to fetch data. Please try again later.")
except ValidationError as e:
    logger.warning(f"Invalid input: {e}")
    st.warning("Please check your input and try again.")
except Exception as e:
    logger.exception("Unexpected error occurred")
    st.error("An unexpected error occurred. Please contact support.")
```

## External API Integration

### MarketRaccoon API

Primary source for historical cryptocurrency prices and fiat exchange rates.

**Configuration:**
- Base URL: Configurable in settings.json (default: http://api.marketraccoon.eu)
- Authentication: Optional X-API-Key header
- Documentation: http://api.marketraccoon.eu/api/yaml

**Key Endpoints:**

1. `/api/v1/cryptocurrency` - Historical crypto prices (USD)
   - Pagination via "next" field
   - Returns time-series price data

2. `/api/v1/cryptocurrency/latests` - Latest crypto prices (USD)
   - Bulk fetch current prices

3. `/api/v1/fiat` - Historical USD↔EUR exchange rates
   - Date-range queries supported
   - Cached locally with FiatCacheManager

4. `/api/v1/fiat/latest` - Current USD/EUR rate
   - Used for real-time conversions

5. `/api/v1/coins` - Token symbol to ID mapping
   - Required for price queries

**Important:** All crypto prices from MarketRaccoon are in USD - requires conversion for EUR display.

**Caching:**
```python
from modules.database.fiat_cache import FiatCacheManager

# FiatCacheManager uses api_cache.json for TTL-based caching
# Reduces API calls for frequently accessed fiat rates
```

### CoinMarketCap API

Primary source for current cryptocurrency prices in EUR.

**Endpoints:**
- `/v2/cryptocurrency/quotes/latest` - Current prices
- `/v2/tools/price-conversion` - Fiat rate conversions

**Debug Mode:** Switches to sandbox API with public key

### RatesDB.com API

Fallback for historical fiat rates when MarketRaccoon unavailable.

**Endpoint:** `https://free.ratesdb.com/v1/rates?from=EUR&to=USD&date={date}`
**Rate Limit:** 1 second sleep between requests

## Currency Conversion Patterns

The application supports EUR ↔ USD conversion with different strategies for current vs historical data.

### Current Rate Conversion

Use `tools.convert_price_to_target_currency()` for single price conversion:

```python
# Converts current USD price to EUR (or vice versa)
price_eur = tools.convert_price_to_target_currency(
    price_usd,
    from_currency="USD",
    to_currency="EUR",
    settings=st.session_state.settings
)
```

**Implementation:**
- Fetches latest USD→EUR rate from MarketRaccoon API
- Uses FiatCacheManager for caching
- USD→EUR: multiply by rate
- EUR→USD: divide by rate

### Historical Rate Conversion

Use `tools.convert_dataframe_prices_historical()` for time-series data:

```python
# Converts historical price series with date-matched rates
df_eur = tools.convert_dataframe_prices_historical(
    df_usd,  # DataFrame with timestamp column
    from_currency="USD",
    to_currency="EUR",
    dbfile=st.session_state.dbfile
)
```

**Implementation:**
- Fetches historical USD→EUR rate series from MarketRaccoon
- Uses `pd.merge_asof` to match each price to nearest rate timestamp
- Ensures accurate historical conversions

### Crypto-to-Crypto Historical Conversion

For calculating historical exchange rates between cryptocurrencies:

```python
# API method (recommended for large datasets)
rate = apimarket.batch_convert_historical_api(
    token_from="BTC",
    token_to="ETH",
    timestamp=1609459200
)

# DB method (uses local Market table)
rate = market.batch_convert_historical(
    token_from="BTC",
    token_to="ETH",
    timestamp=1609459200
)
```

**Use case:** Calculate performance of token swaps (e.g., Operations page)

# Database Architecture and Critical Rules

## SQLite Database Schema

The application uses SQLite (`data/db.sqlite3`) with the following tables:

### Core Tables

1. **TokensDatabase** - Historical token prices and holdings
   - Columns: `timestamp`, `token`, `price`, `count`, `token_id`
   - Primary data source for portfolio valuation
   - **CRITICAL**: May contain duplicate entries - always run `TokensDatabase.drop_duplicate()` after bulk imports

2. **Portfolios** - Portfolio definitions
   - Columns: `id` (AUTOINCREMENT), `name` (UNIQUE), `bundle`
   - Manages multiple portfolio containers (Swissborg, Ledger, Binance, etc.)

3. **Portfolios_Tokens** - Current token holdings per portfolio
   - Columns: `portfolio_id`, `token`, `amount`
   - Foreign key: `portfolio_id` → `Portfolios(id)`
   - Composite primary key: `(portfolio_id, token)`

4. **Operations** - Transaction history
   - Columns: `id`, `type`, `source`, `destination`, `source_unit`, `destination_unit`, `timestamp`, `portfolio`
   - **CRITICAL**: Operations with `source = 0` are VALID - they represent airdrops!
   - Do NOT delete or flag as invalid

5. **Market** - Historical cryptocurrency market data
   - Columns: `timestamp`, `token`, `price`
   - Indexed on `(timestamp, currency)`

6. **Currency** - Fiat currency exchange rates
   - Columns: `timestamp`, `currency`, `price`

7. **Swaps** - Token swap transactions
   - Columns: `id`, `timestamp`, `token_from`, `amount_from`, `wallet_from`, `token_to`, `amount_to`, `wallet_to`, `tag`

8. **TokenMetadata** - Token status tracking (active/delisted)
   - Columns: `token` (PRIMARY KEY), `status`, `delisting_date`, `last_valid_price_date`, `notes`, `created_at`, `updated_at`
   - See `DATABASE_RULES.md` for complete delisted token list

### Database Access Patterns

**Memory-Efficient Data Loading:**
```python
# WRONG - Multiple merges cause memory explosion
for token in tokens:
    df = query_token_data(token)
    df_result = df_result.merge(df, on='timestamp', how='outer')  # ❌ 28GB allocation!

# CORRECT - Use pivot_table for wide-format transformation
df_all = query_all_tokens()
df_result = df_all.pivot_table(
    index='timestamp',
    columns='token',
    values='value',
    fill_value=0
)  # ✅ Efficient memory usage
```

**Token Metadata Integration:**
```python
from modules.token_metadata import TokenMetadataManager

manager = TokenMetadataManager()

# Filter delisted tokens before UI display
active_tokens = manager.filter_active_tokens(all_tokens)

# Check individual token status
if manager.is_token_delisted('MATIC'):
    # Don't show in active portfolio
```

### Critical Database Rules

**⚠️ NEVER DO:**
1. Delete operations with `source = 0` (these are airdrops)
2. Use multiple `merge(..., how='outer')` on TokensDatabase (causes memory explosion)
3. Modify database schema without creating migration scripts
4. Commit database files to git

**✅ ALWAYS DO:**
1. Run `drop_duplicate()` after bulk data imports
2. Use `pivot_table` for wide-format transformations
3. Check token status with `TokenMetadataManager` before displaying
4. Backup database before schema changes

See `DATABASE_RULES.md` for complete validation rules and delisted token list.

## Application Architecture

### Entry Point and Navigation

**Main Application Flow:**
```
app.py (entry point)
  ↓
1. setup_logging() → Configure DEBUG level logging to stdout
2. st.set_page_config(layout="wide") → Streamlit page configuration
3. init_config() → Load settings.json into memory
4. tools.load_settings() → Populate st.session_state.settings
5. setup_navigation() → Define multi-page navigation structure
6. navigator.run() → Start Streamlit page router
  ↓
Streamlit multi-page app with sections:
  - Main: Home, Portfolios, Graphs
  - Tools: Operations, Import, Token Metadata
  - Settings: Configuration
  - Dev: Tests
```

### Page Modules (app_pages/)

- **0_Home.py** - Dashboard with portfolio metrics and update functionality
- **1_Portfolios.py** - Portfolio management and token allocation
- **2_Graphs.py** - Performance visualizations and charts
- **3_Operations.py** - Buy/sell/swap transaction management
- **4_Import.py** - CSV import/export functionality
- **6_Settings.py** - Configuration management
- **X_Tests.py** - Development testing page

### Core Modules

**Database Layer (modules/database/):**
- `tokensdb.py` - Historical token data with time-series operations
- `portfolios.py` - Portfolio CRUD operations
- `operations.py` - Transaction history management
- `market.py` - Market data storage
- `apimarket.py` - External API integration for market data
- `swaps.py` - Token swap transaction management
- `customdata.py` - Key-value configuration storage

**Business Logic:**
- `token_metadata.py` - Token status management (active/delisted)
- `cmc.py` - CoinMarketCap API integration
- `tools.py` - Utility functions and price updates
- `plotter.py` - Chart generation with Plotly
- `configuration.py` - Settings file management
- `aiprocessing.py` - Anthropic Claude API integration for data processing

### State Management

Streamlit session state stores:
- `settings` - Configuration from settings.json (contains API tokens)
- `dbfile` - Path to SQLite database
- `debug_flag` - Debug mode toggle

**Security Note:** Debug mode filters sensitive data (`*_token`, `password`) before display.

### Configuration File (settings.json)

**Complete settings.json structure:**
```json
{
    "MarketRaccoon": {
        "url": "http://api.marketraccoon.eu",
        "token": "optional_api_key"
    },
    "Notion": {
        "token": "optional_notion_token",
        "database": "database_id",
        "parentpage": "page_id"
    },
    "Coinmarketcap": {
        "token": "required_cmc_api_key"
    },
    "AI": {
        "token": "optional_anthropic_api_key"
    },
    "Debug": {
        "flag": "False"
    },
    "Local": {
        "archive_path": "archive",
        "data_path": "data",
        "sqlite_file": "db.sqlite3"
    },
    "OperationsColors": {
        "green_threshold": 100,
        "orange_threshold": 50,
        "red_threshold": 0
    },
    "FiatCurrency": {
        "currency": "EUR"
    },
    "UIPreferences": {
        "show_empty_portfolios": true,
        "graphs_selected_tokens": []
    }
}
```

**Configuration Notes:**
- `MarketRaccoon.token`: Optional API authentication (not required for public endpoints)
- `Coinmarketcap.token`: Required for real-time price updates (public key for debug mode)
- `FiatCurrency.currency`: Set to "EUR" or "USD" for display preference
- `OperationsColors.*`: Thresholds for color-coded transaction visualization
- **Never commit this file with real tokens!**

## Common Development Patterns

### Adding New Token Support

1. Check if token is delisted: `TokenMetadataManager.is_token_delisted(symbol)`
2. If new token, verify it's tracked by CoinMarketCap API
3. Add to portfolio via Portfolios_Tokens table
4. Historical data will populate on next price update

### Price Update Flow

```
User clicks "Update prices" → tools.update()
  ↓
Fetch current portfolio tokens from Portfolios_Tokens
  ↓
Query CoinMarketCap API for current prices
  ↓
Store in TokensDatabase with current timestamp
  ↓
Update last_update in Customdata table
```

### Performance Optimization

**Streamlit Caching:**
```python
@st.cache_data
def load_crypto_data(symbol: str) -> pd.DataFrame:
    # Expensive operation cached by parameters
    return tokensdb.get_token_balances(symbol)
```

**Database Queries:**
- Use indexed columns (`timestamp`, `token`) in WHERE clauses
- Leverage `pivot_table` instead of multiple merges
- Run `drop_duplicate()` regularly to reduce table size

## Known Issues & Workarounds

### Zero Prices in Active Tokens

Some active tokens have historical price entries of 0 due to API errors:

| Token | Zero Price Count | Status | Action |
|-------|------------------|--------|--------|
| SEN   | 187              | ✅ Active | Keep in DB (historical record) |
| MXNA  | 23               | ✅ Active | Keep in DB |
| D2T   | 23               | ✅ Active | Keep in DB |
| LUNA  | 6 (May 2022)     | ✅ Active | LUNA 2.0 crash event |
| TITA  | 2                | ✅ Active | Keep in DB |

**Solution:** These are kept in the database as historical records. Use `TokenMetadataManager` to filter if needed.

### Missing Historical Fiat Rates

If historical USD→EUR rates are unavailable:
- Application logs: "Pas de taux historiques disponibles"
- Fallback: Uses current rate for all historical conversions
- Impact: Slight inaccuracy in historical EUR valuations

### Memory Issues with Large Merges

**Problem:** Multiple `df.merge(..., how='outer')` operations cause memory explosion (28GB+)

**Solution:** Always use `pivot_table` for wide-format transformations:
```python
# ❌ WRONG
df_result = pd.DataFrame()
for token in tokens:
    df = query_token(token)
    df_result = df_result.merge(df, on='timestamp', how='outer')

# ✅ CORRECT
df_all = query_all_tokens()
df_result = df_all.pivot_table(
    index='timestamp',
    columns='token',
    values='value'
)
```

### Duplicate Entries After Import

**Problem:** Bulk CSV imports can create duplicate entries in TokensDatabase

**Solution:** Always run cleanup after imports:
```python
from modules.database.tokensdb import TokensDatabase

tokensdb = TokensDatabase(dbfile)
tokensdb.drop_duplicate()  # Removes duplicates based on (timestamp, token)
```

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
- la documentation de l'API MarketRaccoon est a l'adresse http://api.marketraccoon.eu/api/yaml