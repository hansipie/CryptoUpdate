# CLAUDE.md

This file provides project-specific context for Claude Code when working in this repository.

## Technology Stack

- **Language**: Python 3.x
- **Dependency Management**: uv
- **Web Framework**: Streamlit
- **Containerization**: Docker (port mapping 8042:8080, Streamlit runs on 8080)

## Development Commands

```bash
# Setup and run
uv sync
uv run streamlit run app.py

# Testing (tests/test_utils.py exists but is empty — no active tests there)
uv run pytest

# Code quality
uv run ruff check .
uv run ruff format .
uv run pylint $(git ls-files '*.py')

# Docker
docker compose up
docker compose up --watch   # live reload
```

## Project Structure

- `app.py` — Entry point
- `app_pages/` — Streamlit pages: 0_Home, 1_Portfolios, 2_Graphs, 3_Operations, 4_Import, 5_TokenMetadata, 6_Settings, X_Tests
- `modules/` — Business logic and database layer
- `modules/database/` — DB access classes + migrations
- `data/db.sqlite3` — SQLite database (never commit)
- `settings.json` — Configuration (never commit — contains API keys)

## Application Flow

```
app.py
  ↓ setup_logging()        → DEBUG level to stdout
  ↓ init_config()          → load settings.json
  ↓ tools.load_settings()  → st.session_state.settings
  ↓ run_migrations(dbfile) → apply pending DB migrations (once per session, guarded by session_state)
  ↓ setup_navigation() + navigator.run() → Streamlit multi-page router
```

## Core Modules

**Database Layer (modules/database/):**
- `tokensdb.py` — Historical token prices/holdings, time-series ops
- `portfolios.py` — Portfolio CRUD
- `operations.py` — Transaction history
- `market.py` — Market data storage
- `apimarket.py` — MarketRaccoon API integration
- `swaps.py` — Token swap transactions
- `customdata.py` — Key-value config storage (stores `db_version`)
- `migrations.py` — Versioned schema migrations (v1–v5)

**Business Logic (modules/):**
- `token_metadata.py` — Token status management (active/delisted)
- `cmc.py` — CoinMarketCap API
- `tools.py` — Utility functions, price updates
- `plotter.py` — Plotly chart generation
- `configuration.py` — settings.json management
- `aiprocessing.py` — Anthropic Claude API integration

**Session state:** `settings`, `dbfile`, `debug_flag`
(Debug mode filters `*_token` and `password` fields before display.)

## Database Schema

SQLite at `data/db.sqlite3`. Schema managed by versioned migrations (v1–v5).

### Tables

**TokensDatabase** — Historical token prices/holdings
- `timestamp`, `token`, `price`, `count`, `token_id`
- CRITICAL: may contain duplicates → always run `drop_duplicate()` after bulk imports

**Portfolios** — Portfolio definitions
- `id` (AUTOINCREMENT), `name` (UNIQUE), `bundle`

**Portfolios_Tokens** — Current holdings per portfolio
- `portfolio_id` (FK → Portfolios), `token`, `amount`
- PK: `(portfolio_id, token)`

**Operations** — Transaction history
- `id`, `type`, `source`, `destination`, `source_unit`, `destination_unit`, `timestamp`, `portfolio`
- CRITICAL: `source = 0` = airdrop — DO NOT delete these rows

**Market** — Historical crypto market data
- `timestamp`, `token`, `price` — indexed on `(timestamp, currency)`

**Currency** — Fiat exchange rates
- `timestamp`, `currency`, `price`

**Swaps** — Token swap transactions
- `id`, `timestamp`, `token_from`, `amount_from`, `wallet_from`, `token_to`, `amount_to`, `wallet_to`, `tag`, `note`
- `note TEXT` added in migration v5

**TokenMetadata** — Token status and MarketRaccoon mapping
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT), `token`, `status`, `delisting_date`, `last_valid_price_date`, `notes`, `created_at`, `updated_at`, `mraccoon_id`, `name`
- `id` AUTOINCREMENT added in migration v4 (`token` is no longer the PRIMARY KEY)
- Indexes: `idx_tokenmetadata_token` on `token`, unique index on `mraccoon_id`

**Customdata** — Key-value store
- `id`, `name` (UNIQUE), `value`, `type` — stores `db_version` (int)

### Versioned Migrations (modules/database/migrations.py)

- v1: Create all base tables (TokensDatabase, Portfolios, Operations, Market, Currency, Swaps, TokenMetadata)
- v2: ADD COLUMN `mr_id` INTEGER, `name` TEXT to TokenMetadata
- v3: RENAME COLUMN `mr_id` → `mraccoon_id` in TokenMetadata
- v4: Recreate TokenMetadata with `id` AUTOINCREMENT (removes `token` as PRIMARY KEY, adds indexes)
- v5: ADD COLUMN `note TEXT` to Swaps

### Critical DB Rules

**NEVER:**
- Delete Operations with `source = 0` (these are airdrops)
- Use multiple `merge(..., how='outer')` on TokensDatabase (causes 28GB+ memory explosion)
- Modify the schema without a migration script
- Commit `data/db.sqlite3` to git

**ALWAYS:**
- Run `drop_duplicate()` after bulk data imports
- Use `pivot_table` for wide-format transformations (not repeated outer merges):
  ```python
  df_result = df_all.pivot_table(index='timestamp', columns='token', values='value', fill_value=0)
  ```
- Check token status with `TokenMetadataManager` before displaying

### TokenMetadataManager (modules/token_metadata.py)

- `get_mr_id(token)` → mraccoon_id or None
- `get_all_tokens_df()` → DataFrame(token, mraccoon_id, name) WHERE mraccoon_id IS NOT NULL
- `upsert_token_info(token, mraccoon_id, name)` → INSERT OR UPDATE (preserves status)
- `delete_token(token)` → bool
- `filter_active_tokens(tokens)` → removes delisted tokens
- `is_token_delisted(token)` → bool

## External APIs

### MarketRaccoon API

Base URL: configurable in `settings.json` (`MarketRaccoon.url`, default `http://api.marketraccoon.eu`)
Auth: optional `X-API-Key` header | Docs: http://api.marketraccoon.eu/api/yaml

**All prices from MarketRaccoon are in USD** → requires conversion for EUR display.

Key endpoints:
- `GET /api/v1/cryptocurrency` — Historical crypto prices (USD), paginated via "next"
- `GET /api/v1/cryptocurrency/latests` — Latest crypto prices (bulk)
- `GET /api/v1/fiat` — Historical USD↔EUR rates (date-range queries)
- `GET /api/v1/fiat/latest` — Current USD/EUR rate
- `GET /api/v1/coins` — Token symbol → mraccoon_id mapping (required for price queries)

Fiat rates cached via `FiatCacheManager` (`api_cache.json`, TTL-based).

### CoinMarketCap API

Primary source for current prices in EUR. Debug mode uses sandbox API with public key.
- `GET /v2/cryptocurrency/quotes/latest` — Current prices
- `GET /v2/tools/price-conversion` — Fiat conversions

### RatesDB.com API

Fallback for historical fiat rates when MarketRaccoon unavailable.
- `GET https://free.ratesdb.com/v1/rates?from=EUR&to=USD&date={date}` — Rate limit: 1s/request

## Currency Conversion Patterns

### Current rate (single price)
```python
price_eur = tools.convert_price_to_target_currency(
    price_usd, from_currency="USD", to_currency="EUR",
    settings=st.session_state.settings
)
```
Uses FiatCacheManager → MarketRaccoon `/fiat/latest`. USD→EUR: multiply; EUR→USD: divide.

### Historical rate (time-series DataFrame)
```python
df_eur = tools.convert_dataframe_prices_historical(
    df_usd, from_currency="USD", to_currency="EUR",
    dbfile=st.session_state.dbfile
)
```
Uses `pd.merge_asof` to match each price row to its nearest dated rate.

### Crypto-to-crypto historical
```python
rate = apimarket.batch_convert_historical_api(
    token_from="BTC", token_to="ETH", timestamp=1609459200
)
```
Used by the Operations page to evaluate swap performance.

## Price Update Flow

```
tools.update()
  ↓ Fetch tokens from Portfolios_Tokens
  ↓ Query CoinMarketCap for current prices
  ↓ Store in TokensDatabase with current timestamp
  ↓ Update last_update in Customdata
```

## Configuration File (settings.json)

```json
{
    "MarketRaccoon":    { "url": "http://api.marketraccoon.eu", "token": "" },
    "Notion":           { "token": "", "database": "", "parentpage": "" },
    "Coinmarketcap":    { "token": "required" },
    "AI":               { "token": "" },
    "Debug":            { "flag": "False" },
    "Local":            { "archive_path": "archive", "data_path": "data", "sqlite_file": "db.sqlite3" },
    "OperationsColors": { "green_threshold": 100, "orange_threshold": 50, "red_threshold": 0 },
    "FiatCurrency":     { "currency": "EUR" },
    "UIPreferences":    { "show_empty_portfolios": true, "graphs_selected_tokens": [] }
}
```

- `Coinmarketcap.token` required for price updates (public sandbox key for debug mode)
- `FiatCurrency.currency`: `"EUR"` or `"USD"`
- `OperationsColors.*`: thresholds for color-coded transaction display

## Known Issues

### Zero prices in active tokens

Tokens with historical price = 0 due to API errors (keep as historical records):
SEN (187 entries), MXNA (23), D2T (23), LUNA (6 — May 2022 crash), TITA (2)

### Missing historical fiat rates

Log message: "Pas de taux historiques disponibles" → falls back to current rate for all history (slight EUR inaccuracy).

### Memory explosion with outer merges

Multiple `df.merge(..., how='outer')` on TokensDatabase → 28GB+ allocation.
Always use `pivot_table` instead (see Critical DB Rules above).

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
- la documentation de l'API MarketRaccoon est a l'adresse http://api.marketraccoon.eu/api/yaml
