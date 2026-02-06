# CryptoUpdate - Copilot Instructions

Cryptocurrency portfolio tracking and management application built with Python and Streamlit.

## Development Commands

### Running the Application
```bash
# Start the Streamlit app
uv run streamlit run app.py

# Run with Docker
docker compose up
```

### Code Quality
```bash
# Format code
uv run ruff format .

# Lint and auto-fix issues
uv run ruff check --fix .

# Security audit
uv run pip-audit

# Type checking (if mypy configured)
uv run mypy .
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=.

# Run specific test file
uv run pytest tests/test_utils.py
```

### Dependency Management
```bash
# Install dependencies
uv sync

# Add new package
uv add package-name

# Add dev dependency
uv add --dev package-name

# Update all dependencies
uv lock --upgrade
```

## Architecture Overview

### Application Flow
```
app.py (entry point)
  ↓
setup_logging() → Configure DEBUG level logging
setup_config() → Load settings.json (contains API tokens)
setup_navigation() → Define multi-page structure
  ↓
Streamlit multi-page app:
  - Main: Home, Portfolios, Graphs
  - Tools: Operations, Import, Token Metadata
  - Settings: Configuration
  - Dev: Tests
```

### Module Organization

**Database Layer (`modules/database/`)**
- `tokensdb.py` - Historical token prices and holdings with time-series operations
- `portfolios.py` - Portfolio CRUD operations (Swissborg, Ledger, Binance, etc.)
- `operations.py` - Transaction history (buy/sell/swap)
- `market.py` - Historical cryptocurrency market data storage
- `apimarket.py` - External API integration (CoinMarketCap)
- `swaps.py` - Token swap transaction management
- `fiat_cache.py` - Fiat currency rate caching (EUR/USD)
- `customdata.py` - Key-value configuration storage

**Business Logic (`modules/`)**
- `token_metadata.py` - Token status management (active/delisted/deprecated)
- `cmc.py` - CoinMarketCap API integration for live prices
- `tools.py` - Utility functions and price update orchestration
- `plotter.py` - Plotly chart generation
- `configuration.py` - Settings file (settings.json) management
- `aiprocessing.py` - Anthropic Claude API for data extraction from images

**Application Pages (`app_pages/`)**
- `0_Home.py` - Dashboard with metrics and portfolio overview
- `1_Portfolios.py` - Multi-portfolio management and token allocation
- `2_Graphs.py` - Performance visualizations with Plotly
- `3_Operations.py` - Transaction recording (buy/sell/swap)
- `4_Import.py` - CSV import/export for bulk operations
- `5_TokenMetadata.py` - Token status management UI
- `6_Settings.py` - Configuration interface
- `X_Tests.py` - Development testing page

### State Management
Streamlit session state stores:
- `settings` - Configuration dict from settings.json (includes API tokens)
- `dbfile` - Path to SQLite database (`data/db.sqlite3`)
- `debug_flag` - Debug mode toggle (filters sensitive data before display)

## Database Schema (SQLite)

### Critical Database Rules

**⚠️ NEVER DO:**
1. Delete operations with `source = 0` (these are VALID airdrops!)
2. Use multiple `merge(..., how='outer')` on TokensDatabase (causes 28GB+ memory explosion)
3. Modify database schema without backup and migration scripts
4. Commit database files (`data/db.sqlite3`) to git

**✅ ALWAYS DO:**
1. Run `TokensDatabase.drop_duplicate()` after bulk imports
2. Use `pivot_table()` for wide-format transformations (memory efficient)
3. Check token status with `TokenMetadataManager` before UI display
4. Backup database before schema changes

### Memory-Efficient Data Loading Pattern

```python
# ❌ WRONG - Multiple merges cause memory explosion
for token in tokens:
    df = query_token_data(token)
    df_result = df_result.merge(df, on='timestamp', how='outer')  # Memory bomb!

# ✅ CORRECT - Use pivot_table for wide-format transformation
df_all = query_all_tokens()
df_result = df_all.pivot_table(
    index='timestamp',
    columns='token',
    values='value',
    fill_value=0
)  # Efficient memory usage
```

### Key Tables

- **TokensDatabase** - Historical token prices/holdings (may have duplicates)
- **Portfolios** - Portfolio definitions (id AUTOINCREMENT, name UNIQUE)
- **Portfolios_Tokens** - Current holdings (portfolio_id, token, amount)
- **Operations** - Transaction history (airdrops have source=0)
- **Market** - Historical market data (indexed on timestamp, token)
- **Currency** - Fiat exchange rates (EUR/USD)
- **Swaps** - Token swap transactions
- **TokenMetadata** - Token status tracking (active/delisted)

See `DATABASE_RULES.md` for complete schema and validation rules.

## Code Conventions

### Python Style
- Follow PEP 8 guidelines
- Use type hints on function parameters and returns
- Write docstrings for modules, classes, and non-trivial functions
- Keep functions focused and small

### Streamlit Patterns

**Caching expensive operations:**
```python
@st.cache_data
def load_crypto_data(symbol: str) -> pd.DataFrame:
    """Load and cache cryptocurrency data."""
    return tokensdb.get_token_balances(symbol)
```

**Session state for persistence:**
```python
if 'portfolio_data' not in st.session_state:
    st.session_state.portfolio_data = load_data()
```

**Page configuration:**
```python
st.set_page_config(
    page_title="CryptoUpdate",
    page_icon="📈",
    layout="wide"
)
```

**Error handling:**
```python
try:
    result = fetch_crypto_data(symbol)
except APIError as e:
    logger.error(f"API error: {e}")
    st.error("Unable to fetch data. Please try again later.")
```

### Token Metadata Management

**Always check token status before displaying:**
```python
from modules.token_metadata import TokenMetadataManager

manager = TokenMetadataManager()

# Filter delisted tokens
active_tokens = manager.filter_active_tokens(all_tokens)

# Check individual token
if manager.is_token_delisted('MATIC'):
    # Don't show in active portfolio (migrated to POL)
    pass
```

**Known delisted tokens:** KYROS, ANV, ANC, FXS, MATIC (see DATABASE_RULES.md)

## Configuration

### settings.json Structure
```json
{
    "Coinmarketcap": {"token": "your-api-key"},
    "AI": {"token": "anthropic-api-key"},
    "Debug": {"flag": "False"},
    "Local": {
        "archive_path": "archive",
        "data_path": "data",
        "sqlite_file": "db.sqlite3"
    }
}
```

**Security:** Never commit `settings.json` with real API keys. Debug mode automatically redacts sensitive data (`*_token`, `password`) from logs.

## Common Development Patterns

### Adding Token Support
1. Check if delisted: `TokenMetadataManager.is_token_delisted(symbol)`
2. Verify token exists on CoinMarketCap
3. Add to portfolio via Portfolios_Tokens table
4. Historical data populates on next price update

### Price Update Flow
```
User clicks "Update prices" → tools.update()
  ↓
Fetch current tokens from Portfolios_Tokens
  ↓
Query CoinMarketCap API for current prices
  ↓
Store in TokensDatabase with timestamp
  ↓
Update last_update in Customdata table
```

### Performance Optimization
- Use indexed columns (`timestamp`, `token`) in WHERE clauses
- Use `pivot_table()` instead of multiple merges for wide data
- Run `drop_duplicate()` regularly to reduce table size
- Cache Streamlit expensive operations with `@st.cache_data`

## External APIs

- **CoinMarketCap API** - Live cryptocurrency prices (required)
- **Anthropic Claude API** - AI-powered data extraction from images (optional)

## Technology Stack

- **Python 3.12+** - Required Python version
- **uv** - Fast Python package manager (replaces pip)
- **Streamlit** - Web framework for data apps
- **Pandas** - Data manipulation
- **Plotly** - Interactive charts
- **SQLite** - Local database
- **Docker** - Containerization

## Additional Resources

- `README.md` - Full feature list and setup guide
- `CLAUDE.md` - Detailed development guidelines and Archon workflow
- `DATABASE_RULES.md` - Complete database schema and validation rules
- `SECURITY.md` - Security guidelines
