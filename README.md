# CryptoUpdate

Cryptocurrency portfolio tracking and management application with Streamlit web interface.

## Features

### Portfolio Management
- 📊 **Real-time Portfolio Tracking** - Monitor total portfolio value, invested amount, and profit/loss
- 💰 **Multi-Portfolio Support** - Manage multiple portfolios (Swissborg, Ledger, Binance, etc.)
- 🔄 **Portfolio Aggregation** - View combined holdings across all portfolios
- 📈 **Historical Balance Tracking** - Track portfolio value over time with timestamp-based records

### Market Data & Pricing
- 💱 **Live Price Updates** - Fetch current cryptocurrency prices via CoinMarketCap API
- 💲 **Multi-Currency Support** - EUR/USD fiat currency conversion with file-based caching
- 📉 **Historical Market Data** - Store and query historical price data
- 🕒 **Price Interpolation** - Fill missing historical prices for accurate valuations

### Visualizations & Analytics
- 📊 **Interactive Graphs** - Portfolio performance visualization with Plotly
- 🥧 **Pie Charts** - Portfolio allocation and token distribution
- 📈 **Time-Series Analysis** - Value trends and performance metrics over time
- 💹 **Performance Metrics** - Investment returns, profit/loss, percentage gains

### Transaction Management
- 🛒 **Buy/Sell Operations** - Track purchase and sale transactions
- 🔄 **Token Swaps** - Record token exchange operations
- 💸 **Transaction History** - Complete audit trail of all operations
- 🎁 **Airdrop Support** - Handle zero-cost token acquisitions

### Data Management
- 📥 **CSV Import/Export** - Bulk data import and backup capabilities
- 🤖 **AI-Powered Processing** - Anthropic Claude integration for data extraction from screenshots
- 🏷️ **Token Metadata Management** - Track token status (active/delisted/migrated)
- 🗄️ **SQLite Database** - Robust local data storage with multiple specialized tables
- 🧹 **Data Deduplication** - Automatic cleanup of duplicate historical entries

### Advanced Features
- 🔍 **Token Status Tracking** - Manage delisted, deprecated, and migrated tokens
- ⚙️ **Configurable Settings** - Customizable configuration via JSON
- 🐛 **Debug Mode** - Enhanced logging with sensitive data filtering
- 📱 **Responsive UI** - Wide layout with multi-page navigation
- ⏱️ **Update Timestamps** - Track last data refresh with time-since display

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
# Install dependencies
uv sync

# Or create virtual environment and install
uv venv
uv pip install -e .
```

### Setup

Configure environment variables in `settings.json`:
```json
{
    "Coinmarketcap": {
        "token": "your-coinmarketcap-token"
    },
    "AI": {
        "token": "your-anthropic-api-key"
    },
    "Debug": {
        "flag": "False"
    },
    "Local": {
        "archive_path": "archive",
        "data_path": "data",
        "sqlite_file": "db.sqlite3"
    }
}
```

**Required API Keys:**
- **CoinMarketCap**: For fetching cryptocurrency market data and prices
- **Anthropic Claude** (optional): For AI-powered data extraction from images

**Note**: Never commit `settings.json` with real API keys to version control.

## Usage

### Local Development

Launch the application with uv:
```bash
# Run the main portfolio page
uv run streamlit run app.py
```

### Docker Usage

Run the containerized application:
```bash
# Using pre-built image
docker run -p 8501:8501 crypto-update

# With volume mount for development
docker run -p 8501:8501 -v $(pwd):/app crypto-update
```

The web interface will be available at http://localhost:8501

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
│   ├── 5_TokenMetadata.py   # Token status management
│   ├── 6_Settings.py        # Configuration
│   └── X_Tests.py           # Development testing page
├── modules/                  # Core business logic
│   ├── database/            # Database layer
│   │   ├── tokensdb.py     # Historical token data
│   │   ├── portfolios.py   # Portfolio CRUD operations
│   │   ├── operations.py   # Transaction history
│   │   ├── market.py       # Market data storage
│   │   ├── apimarket.py    # External API integration
│   │   ├── swaps.py        # Token swap transactions
│   │   ├── fiat_cache.py   # Fiat currency caching
│   │   └── customdata.py   # Key-value config storage
│   ├── aiprocessing.py      # Anthropic Claude API integration
│   ├── cmc.py              # CoinMarketCap API
│   ├── token_metadata.py   # Token status tracking
│   ├── tools.py            # Utility functions
│   ├── plotter.py          # Plotly chart generation
│   ├── configuration.py    # Settings management
│   └── utils.py            # General utilities
├── data/                    # Application data
│   ├── db.sqlite3          # SQLite database
│   └── fiat_cache/         # Cached fiat currency rates
├── tests/                   # Test files
├── Dockerfile              # Docker configuration
├── pyproject.toml          # Python project configuration
├── uv.lock                 # Locked dependencies
├── CLAUDE.md               # Development instructions
└── DATABASE_RULES.md       # Database schema and rules
```

## Technologies Used

### Core Stack
- **Python 3.8+**: Programming language
- **uv**: Ultra-fast Python package manager and dependency resolver
- **Streamlit**: Web application framework for data apps
- **Docker**: Containerization for deployment

### Libraries & APIs
- **Pandas**: Data manipulation and analysis
- **SQLite**: Lightweight database
- **Plotly**: Interactive charting and visualizations
- **Anthropic Claude**: AI-powered data extraction from images (optional)
- **CoinMarketCap API**: Cryptocurrency market data

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

# Run pylint
uv run pylint modules/ app_pages/

# Security audit
uv run pip-audit
```

### Development Commands

```bash
# Install new dependency
uv add package-name

# Install dev dependency
uv add --dev package-name

# Update dependencies
uv lock --upgrade

# Sync dependencies
uv sync
```

### Database Management

The application uses SQLite with multiple tables for different data types:
- **TokensDatabase**: Historical token prices and holdings
- **Portfolios**: Portfolio definitions
- **Portfolios_Tokens**: Current token holdings per portfolio
- **Operations**: Transaction history
- **Market**: Historical cryptocurrency market data
- **Currency**: Fiat currency exchange rates
- **Swaps**: Token swap transactions
- **TokenMetadata**: Token status tracking

See `DATABASE_RULES.md` for complete schema documentation and critical rules.

### Key Development Guidelines

1. **Memory-Efficient Queries**: Use `pivot_table()` instead of multiple `merge()` operations on large datasets
2. **Data Deduplication**: Run `TokensDatabase.drop_duplicate()` after bulk imports
3. **Token Status**: Always check token metadata before displaying in UI
4. **Airdrop Operations**: Operations with `source = 0` are valid (airdrops)
5. **Configuration**: Never commit `settings.json` with real API tokens

## Application Pages

The application is organized into several pages accessible via navigation:

### Main Section
- **Home (0_Home.py)**: Dashboard with portfolio overview, metrics (invested/total value/profit), performance graphs, and price update functionality
- **Portfolios (1_Portfolios.py)**: Manage multiple portfolios, view token allocations, and aggregate holdings
- **Graphs (2_Graphs.py)**: Interactive performance visualizations with time-series charts and pie charts

### Tools Section
- **Operations (3_Operations.py)**: Record buy, sell, and swap transactions
- **Import (4_Import.py)**: Bulk import/export portfolio data via CSV
- **Token Metadata (5_TokenMetadata.py)**: Manage token status (active/delisted/deprecated/migrated)

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

## Acknowledgments

Originally inspired by cryptocurrency portfolio tracking needs and community tools.
