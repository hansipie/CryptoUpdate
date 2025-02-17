"""Configuration management module for CryptoUpdate application."""

import json
import logging
import os

logger = logging.getLogger(__name__)

class configuration:
    """Manages application configuration from JSON file."""

    def __init__(self, config_file: str = "./settings.json"):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to JSON configuration file
        """
        logger.debug("Loading configuration")
        self.config_file = config_file
        self.conf = None

    def readConfig(self):
        """Read configuration from JSON file.
        
        Raises:
            FileNotFoundError: If settings file doesn't exist
            JSONDecodeError: If settings file is invalid JSON
        """
        if not os.path.exists(self.config_file):
            logger.error("Settings file not found: " + self.config_file)
            raise FileNotFoundError
        
        with open(self.config_file, 'r') as f:
            self.conf = json.load(f)

    def saveConfig(self, settings: dict):
        """Save configuration to JSON file.
        
        Args:
            settings: Dictionary containing settings to save
        """
        logger.debug("Saving configuration")
        config = {
            "MarketRaccoon": {
                "url": settings["marketraccoon_url"]
            },
            "Notion": {
                "token": settings["notion_token"],
                "database": settings["notion_database"], 
                "parentpage": settings["notion_parentpage"]
            },
            "Coinmarketcap": {
                "token": settings["coinmarketcap_token"]
            },
            "OpenAI": {
                "token": settings["openai_token"]
            },
            "Debug": {
                "flag": str(settings["debug_flag"])
            },
            "Local": {
                "archive_path": os.path.basename(settings["archive_path"]).replace("debug_", ""),
                "data_path": os.path.basename(settings["data_path"]), 
                "sqlite_file": os.path.basename(settings["dbfile"]).replace("debug_", "")
            }
        }

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logger.error("Error saving configuration: %s - %s", type(e).__name__, str(e))
            raise
