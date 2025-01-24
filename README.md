# CryptoUpdate

Cryptocurrency portfolio tracking and management application with Streamlit web interface.

## Features

- 📊 Real-time portfolio value tracking
- 💱 Buy and swap operations management
- 📈 Performance visualization with graphs
- 📥 Data import/export
- 🔄 Notion synchronization
- 💰 Multi-currency support (EUR/USD)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/CryptoUpdate.git
cd CryptoUpdate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables in `settings.json`:
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

Launch the application:
```bash
streamlit run app.py
```

The web interface will be available at http://localhost:8501

## Project Structure

```
CryptoUpdate/
├── app.py                  # Application entry point
├── app_pages/             # Application pages
│   ├── 0_Home.py         # Main dashboard
│   ├── 1_Portfolios.py   # Portfolio management
│   ├── 2_Graphs.py       # Visualizations
│   ├── 3_Operations.py   # Buy/Swap operations
│   ├── 4_Import.py       # Import/Export
│   └── 6_Settings.py     # Configuration
├── modules/              # Project modules
│   ├── database/        # Database management
│   ├── utils.py         # Utilities
│   └── ...
├── data/                # Data
└── requirements.txt     # Python dependencies
```

## Technologies Used

- Python 3.8+
- Streamlit
- Pandas
- SQLite
- CoinMarketCap API
- Notion API

## Contributing

Contributions are welcome! Feel free to:
1. Fork the project
2. Create a branch (`git checkout -b feature/NewFeature`)
3. Commit your changes (`git commit -am 'Add NewFeature'`)
4. Push to the branch (`git push origin feature/NewFeature`)
5. Open a Pull Request

## Credits

- https://github.com/tnvmadhav/notion-crypto-integration (update notion database)
- https://github.com/yannbolliger/notion-exporter (download database to a CSV file)
