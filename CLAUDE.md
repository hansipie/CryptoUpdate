# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application
```bash
streamlit run app.py
```
The web interface will be available at http://localhost:8501

### Code Quality
```bash
# Linting (configured in pyproject.toml)
ruff check .

# Formatting
ruff format .
```

### Dependencies
- Install: `pip install -r requirements.txt` or `uv pip install -r requirements.txt`
- The project uses `uv` for dependency management with `uv.lock`

### Testing
- Test page available at: `/tests` in the web interface (app_pages/X_Tests.py)

## Architecture Overview

### Application Structure
This is a **Streamlit-based cryptocurrency portfolio tracking application** with the following architecture:

- **Entry Point**: `app.py` - Sets up logging, configuration, and navigation
- **Pages**: `app_pages/` - Individual Streamlit pages for different features
- **Database Layer**: `modules/database/` - SQLite-based data persistence
- **Core Modules**: `modules/` - Business logic and utilities

### Key Components

#### Navigation Structure
The app uses Streamlit's native navigation with these main sections:
- **Main**: Home, Portfolios, Graphs
- **Tools**: Operations, Import
- **Settings**: Configuration management
- **Dev**: Tests and debugging

#### Database Architecture
- **SQLite database** stored in `data/db.sqlite3`
- **Modular database classes** in `modules/database/`:
  - `portfolios.py` - Portfolio and token balance management
  - `operations.py` - Buy/sell operations
  - `market.py` - Price data
  - `tokensdb.py` - Token information and aggregations
  - `swaps.py` - Token swap operations

#### Configuration System
- **JSON-based configuration** in `settings.json`
- **Required API tokens**: Notion, CoinMarketCap, OpenAI
- **Debug mode support** with prefixed file names
- **Configuration class** in `modules/configuration.py`

### Data Flow
1. **Price Updates**: External APIs → Market database → Portfolio calculations
2. **Portfolio Management**: User input → Database operations → Real-time updates
3. **Visualization**: Database queries → Pandas DataFrames → Plotly/Matplotlib charts
4. **External Sync**: Notion API integration for portfolio synchronization

### Key Patterns
- **Session state management** for settings and data caching
- **Database connection context managers** for SQLite operations
- **Spinner components** for long-running operations with timing
- **Error handling** with user-friendly Streamlit error messages
- **Logging configuration** with DEBUG level and structured formatting

### External Integrations
- **Notion API** for portfolio synchronization
- **CoinMarketCap API** for price data
- **OpenAI API** for AI processing features
- **Market Raccoon API** for additional market data

## Development Notes

### File Naming Conventions
- Pages use numbered prefixes: `0_Home.py`, `1_Portfolios.py`, etc.
- Debug mode adds `debug_` prefix to database files
- Test files use `X_` prefix

### Database Schema
The application maintains several key tables:
- `Portfolios` - Portfolio definitions
- `Portfolios_Tokens` - Token balances per portfolio
- `Operations` - Transaction history
- `Market` - Price data over time

### Settings Configuration
Ensure `settings.json` exists with required API tokens and paths before running the application. The configuration class handles file validation and error reporting.