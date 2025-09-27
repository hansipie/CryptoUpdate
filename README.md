# CryptoUpdate

Cryptocurrency portfolio tracking and management application with Streamlit web interface.

## Features

- 📊 Real-time portfolio value tracking
- 💱 Buy and swap operations management
- 📈 Performance visualization with graphs
- 📥 Data import/export
- 💰 Multi-currency support (EUR/USD)

## Installation

### Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) (ultra-fast Python package manager)
- Docker (optional, for containerized deployment)

### Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/CryptoUpdate.git
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
    "Notion": {
        "token": "your-notion-token",
        "database": "your-database-name",
        "parentpage": "your-parent-page"
    },
    "Coinmarketcap": {
        "token": "your-coinmarketcap-token"
    },
    "OpenAI": {
        "token": "your-openai-token"
    },
    "Debug": {
        "flag": "False"
    },
    "Local": {
        "archive_path": "archive",
        "data_path": "data",
        "sqlite_file": "cryptodb.sqlite"
    }
}
```

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
├── app_pages/             # Streamlit application pages
│   ├── 1_Portfolios.py   # Portfolio management (main entry point)
│   ├── 2_Graphs.py       # Visualizations
│   ├── 3_Operations.py   # Buy/Swap operations
│   ├── 4_Import.py       # Import/Export
│   └── 6_Settings.py     # Configuration
├── modules/              # Project modules
│   ├── database/        # Database management
│   ├── utils.py         # Utilities
│   └── ...
├── tests/               # Test files
├── data/               # Application data
├── Dockerfile          # Docker configuration
├── pyproject.toml      # Python project configuration
├── uv.lock            # Locked dependencies
└── CLAUDE.md          # Development instructions
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
- **CoinMarketCap API**: Cryptocurrency market data
- **Notion API**: Notion workspace integration

### Development Tools
- **pytest**: Testing framework
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checking

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=.

# Run specific test file
uv run pytest tests/test_specific.py
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Type checking
uv run mypy .
```

### Development Commands

```bash
# Install new dependency
uv add package-name

# Install dev dependency
uv add --dev pytest

# Update dependencies
uv lock --upgrade

# Sync dependencies
uv sync
```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the project
2. Create a feature branch (`git checkout -b feature/NewFeature`)
3. Install dependencies with `uv sync`
4. Make your changes following the code style guidelines
5. Run tests with `uv run pytest`
6. Run code quality checks with `uv run ruff check .` and `uv run ruff format .`
7. Commit your changes (`git commit -am 'Add NewFeature'`)
8. Push to the branch (`git push origin feature/NewFeature`)
9. Open a Pull Request

See `CLAUDE.md` for detailed development guidelines and project-specific instructions.

## Credits

- https://github.com/tnvmadhav/notion-crypto-integration (update notion database)
- https://github.com/yannbolliger/notion-exporter (download database to a CSV file)
