# CryptoUpdate

Cryptocurrency portfolio tracking and management application with Streamlit web interface.

## Features

### Portfolio Management
- **Real-time Portfolio Tracking** - Monitor total portfolio value, invested amount, and profit/loss
- **Multi-Portfolio Support** - Manage multiple portfolios (Swissborg, Ledger, Binance, etc.)
- **Portfolio Aggregation** - View combined holdings across all portfolios
- **Historical Balance Tracking** - Track portfolio value over time with timestamp-based records

### Market Data & Pricing
- **Live Price Updates** - Fetch current cryptocurrency prices via CoinMarketCap API
- **Historical Market Data** - Retrieve and store historical prices via MarketRaccoon API
- **Multi-Currency Support** - EUR/USD fiat currency conversion with file-based caching
- **Price Interpolation** - Fill missing historical prices for accurate valuations

### Visualizations & Analytics
- **Interactive Graphs** - Portfolio performance visualization with Plotly
- **Pie Charts** - Portfolio allocation and token distribution
- **Time-Series Analysis** - Value trends and performance metrics over time
- **Performance Metrics** - Investment returns, profit/loss, percentage gains

### Transaction Management
- **Buy/Sell Operations** - Track purchase and sale transactions
- **Token Swaps** - Record token exchange operations
- **Transaction History** - Complete audit trail of all operations
- **Airdrop Support** - Handle zero-cost token acquisitions (source = 0)

### Data Management
- **CSV Import/Export** - Bulk data import and backup capabilities
- **AI-Powered Processing** - Anthropic Claude integration for data extraction from screenshots
- **Token Metadata Management** - Track token status (active/delisted/migrated) with MarketRaccoon ID mapping
- **SQLite Database** - Robust local data storage with versioned schema migrations
- **Data Deduplication** - Automatic cleanup of duplicate historical entries

### Advanced Features
- **Token Status Tracking** - Manage delisted, deprecated, and migrated tokens
- **Configurable Settings** - Customizable configuration via JSON
- **Debug Mode** - Enhanced logging with sensitive data filtering
- **Responsive UI** - Wide layout with multi-page navigation
- **Update Timestamps** - Track last data refresh with time-since display

## Installation

### Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) (ultra-fast Python package manager)
- Docker (optional, for containerized deployment)

### Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/hansipie/CryptoUpdate.git
cd CryptoUpdate
```

2. Install dependencies with uv:
```bash
uv sync
```

### Setup

Configure `settings.json` at the root of the project:
```json
{
    "MarketRaccoon":    { "url": "http://api.marketraccoon.eu", "token": "" },
    "Coinmarketcap":    { "token": "your-coinmarketcap-token" },
    "AI":               { "token": "your-anthropic-api-key" },
    "Notion":           { "token": "", "database": "", "parentpage": "" },
    "Debug":            { "flag": "False" },
    "Local":            { "archive_path": "archive", "data_path": "data", "sqlite_file": "db.sqlite3" },
    "OperationsColors": { "green_threshold": 100, "orange_threshold": 50, "red_threshold": 0 },
    "FiatCurrency":     { "currency": "EUR" },
    "UIPreferences":    { "show_empty_portfolios": true, "graphs_selected_tokens": [] }
}
```

**Required API Keys:**
- **CoinMarketCap**: For fetching current cryptocurrency prices
- **Anthropic Claude** (optional): For AI-powered data extraction from images

**Note**: Never commit `settings.json` with real API keys to version control.

## Usage

### Local Development

```bash
uv run streamlit run app.py
```

The web interface will be available at http://localhost:8501

### Docker

```bash
# Build and run with docker compose
docker compose up

# With live reload
docker compose up --watch
```

The web interface will be available at http://localhost:8042 (mapped from container port 8080).

## Project Structure

```
CryptoUpdate/
├── app.py                    # Main entry point and navigation
├── app_pages/                # Streamlit application pages
│   ├── 0_Home.py            # Dashboard with metrics and graphs
│   ├── 1_Portfolios.py      # Portfolio management
│   ├── 2_Graphs.py          # Performance visualizations
│   ├── 3_Operations.py      # Transaction management (Buy/Swap)
│   ├── 4_Import.py          # CSV import/export
│   ├── 5_TokenMetadata.py   # Token status and MarketRaccoon ID management
│   ├── 6_Settings.py        # Configuration
│   └── X_Tests.py           # Development testing page
├── modules/                  # Core business logic
│   ├── database/            # Database layer
│   │   ├── migrations.py   # Versioned schema migrations (v1–v5)
│   │   ├── tokensdb.py     # Historical token data
│   │   ├── portfolios.py   # Portfolio CRUD operations
│   │   ├── operations.py   # Transaction history
│   │   ├── market.py       # Market data storage
│   │   ├── apimarket.py    # MarketRaccoon API integration
│   │   ├── swaps.py        # Token swap transactions
│   │   ├── fiat_cache.py   # Fiat currency caching
│   │   └── customdata.py   # Key-value config storage
│   ├── aiprocessing.py      # Anthropic Claude API integration
│   ├── cmc.py              # CoinMarketCap API
│   ├── token_metadata.py   # Token status tracking
│   ├── tools.py            # Utility functions
│   ├── plotter.py          # Plotly chart generation
│   └── configuration.py    # Settings management
├── data/                    # Application data (not committed)
│   └── db.sqlite3          # SQLite database
├── tests/                   # Test files
├── Dockerfile              # Docker configuration
├── pyproject.toml          # Python project configuration
├── uv.lock                 # Locked dependencies
└── CLAUDE.md               # Development instructions for Claude Code
```

## Technologies Used

### Core Stack
- **Python 3.8+**: Programming language
- **uv**: Ultra-fast Python package manager and dependency resolver
- **Streamlit**: Web application framework for data apps
- **Docker**: Containerization for deployment

### Libraries & APIs
- **Pandas**: Data manipulation and analysis
- **SQLite**: Lightweight database with versioned migrations
- **Plotly**: Interactive charting and visualizations
- **MarketRaccoon API**: Historical cryptocurrency prices and fiat exchange rates
- **CoinMarketCap API**: Current cryptocurrency market data
- **Anthropic Claude**: AI-powered data extraction from images (optional)

### Development Tools
- **ruff**: Fast Python linter and formatter
- **pylint**: Code quality checker
- **pip-audit**: Security vulnerability scanner

## Development

### Code Quality

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Fix linting issues automatically
uv run ruff check --fix .

# Run pylint (all tracked Python files)
uv run pylint $(git ls-files '*.py')

# Security audit
uv run pip-audit
```

### Dependency Management

```bash
uv add package-name         # Add dependency
uv add --dev package-name   # Add dev dependency
uv lock --upgrade           # Update all dependencies
uv sync                     # Sync environment to lockfile
```

### Database Management

The application uses SQLite with versioned schema migrations (v1–v5, applied automatically at startup).

Tables:
- **TokensDatabase**: Historical token prices and holdings
- **Portfolios**: Portfolio definitions
- **Portfolios_Tokens**: Current token holdings per portfolio
- **Operations**: Transaction history (source=0 = airdrop, do not delete)
- **Market**: Historical cryptocurrency market data
- **Currency**: Fiat currency exchange rates
- **Swaps**: Token swap transactions (includes `note` column)
- **TokenMetadata**: Token status, MarketRaccoon ID mapping (`id`, `token`, `mraccoon_id`, `name`, `status`, ...)
- **Customdata**: Key-value configuration store

### Key Development Guidelines

1. **Memory-Efficient Queries**: Use `pivot_table()` instead of multiple `merge()` operations on large datasets
2. **Data Deduplication**: Run `TokensDatabase.drop_duplicate()` after bulk imports
3. **Token Status**: Always check token metadata before displaying in UI
4. **Airdrop Operations**: Operations with `source = 0` are valid (airdrops) — never delete them
5. **Configuration**: Never commit `settings.json` with real API tokens

## Application Pages

### Main Section
- **Home (0_Home.py)**: Dashboard with portfolio overview, metrics (invested/total value/profit), performance graphs, and price update functionality
- **Portfolios (1_Portfolios.py)**: Manage multiple portfolios, view token allocations, and aggregate holdings
- **Graphs (2_Graphs.py)**: Interactive performance visualizations with time-series charts and pie charts

### Tools Section
- **Operations (3_Operations.py)**: Record buy, sell, and swap transactions
- **Import (4_Import.py)**: Bulk import/export portfolio data via CSV
- **Token Metadata (5_TokenMetadata.py)**: Manage token status (active/delisted/deprecated/migrated) and MarketRaccoon ID mapping

### Settings Section
- **Settings (6_Settings.py)**: Configure application settings and API tokens

### Dev Section
- **Tests (X_Tests.py)**: Development testing interface

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the project
2. Create a feature branch (`git checkout -b feature/NewFeature`)
3. Install dependencies with `uv sync`
4. Make your changes following the code style guidelines in `CLAUDE.md`
5. Run code quality checks: `uv run ruff check .` and `uv run ruff format .`
6. Test your changes locally with `uv run streamlit run app.py`
7. Commit your changes (`git commit -am 'Add NewFeature'`)
8. Push to the branch (`git push origin feature/NewFeature`)
9. Open a Pull Request

See `CLAUDE.md` for detailed development guidelines and project-specific instructions.

## License

This project is licensed under the terms specified in the LICENSE file.
