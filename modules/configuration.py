"""Configuration management module for CryptoUpdate application."""

import json
import logging
import os

logger = logging.getLogger(__name__)


class Configuration:
    """Manages application configuration from JSON file."""

    def __init__(self, config_file: str = "./settings.json"):
        """Initialize configuration manager.

        Args:
            config_file: Path to JSON configuration file
        """
        logger.debug("Loading configuration")
        self.config_file = config_file
        self.conf = None

    def read_config(self):
        """Read configuration from JSON file.

        Raises:
            FileNotFoundError: If settings file doesn't exist
            JSONDecodeError: If settings file is invalid JSON
        """
        if not os.path.exists(self.config_file):
            logger.error("Settings file not found: %s", self.config_file)
            raise FileNotFoundError

        with open(self.config_file, "r", encoding="utf-8") as f:
            self.conf = json.load(f)

    def save_config(self, settings: dict):
        """Save configuration to JSON file.

        Args:
            settings: Dictionary containing settings to save
        """
        logger.debug("Saving configuration")

        project_root = os.path.abspath(os.getcwd())

        def _project_relative(path: str) -> str:
            """Return a project-relative path when possible, preserving subfolders."""
            abs_path = os.path.abspath(path)
            return os.path.relpath(abs_path, project_root)

        def _strip_debug_prefix(path: str) -> str:
            """Remove debug_ prefix only from final filename component."""
            directory, filename = os.path.split(path)
            if filename.startswith("debug_"):
                filename = filename[len("debug_") :]
            return os.path.join(directory, filename) if directory else filename

        data_path = _project_relative(settings["data_path"])
        archive_path = _strip_debug_prefix(_project_relative(settings["archive_path"]))

        db_abs = os.path.abspath(settings["dbfile"])
        data_abs = os.path.abspath(settings["data_path"])
        sqlite_file = os.path.relpath(db_abs, data_abs)
        if sqlite_file.startswith(".."):
            sqlite_file = os.path.basename(db_abs)
        sqlite_file = _strip_debug_prefix(sqlite_file)

        config = {
            "MarketRaccoon": {
                "url": settings["marketraccoon_url"],
                "token": settings.get("marketraccoon_token", ""),
            },
            "RatesDB": {
                "url": settings.get(
                    "ratesdb_url", "https://free.ratesdb.com/v1/rates"
                )
            },
            "Notion": {
                "token": settings["notion_token"],
                "database": settings["notion_database"],
                "parentpage": settings["notion_parentpage"],
            },
            "Coinmarketcap": {"token": settings["coinmarketcap_token"]},
            "AI": {"token": settings["ai_apitoken"]},
            "Debug": {"flag": str(settings["debug_flag"])},
            "Local": {
                "archive_path": archive_path,
                "data_path": data_path,
                "sqlite_file": sqlite_file,
            },
            "OperationsColors": {
                "green_threshold": settings.get("operations_green_threshold", 100),
                "orange_threshold": settings.get("operations_orange_threshold", 50),
                "red_threshold": settings.get("operations_red_threshold", 0),
            },
            "FiatCurrency": {
                "currency": settings.get("fiat_currency", "EUR"),
            },
            "UIPreferences": {
                "show_empty_portfolios": settings.get("show_empty_portfolios", True),
                "graphs_selected_tokens": settings.get("graphs_selected_tokens", []),
            },
        }

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logger.error(
                "Error saving configuration: %s - %s", type(e).__name__, str(e)
            )
            raise
