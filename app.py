"""Main entry point for CryptoUpdate application.

This module initializes the Streamlit application, sets up logging,
loads configuration and defines the navigation structure.
The application provides a web interface for tracking and managing
cryptocurrency portfolios.
"""

# Standard library imports
import logging
import os
import sys

# Third-party imports
import streamlit as st

# Local imports
from modules import tools
from modules.configuration import Configuration as cfg

# Application constants
APP_PAGES = {
    "HOME": "app_pages/0_Home.py",
    "PORTFOLIOS": "app_pages/1_Portfolios.py",
    "GRAPHS": "app_pages/2_Graphs.py",
    "OPERATIONS": "app_pages/3_Operations.py",
    "IMPORT": "app_pages/4_Import.py",
    "TOKEN_METADATA": "app_pages/5_TokenMetadata.py",
    "SETTINGS": "app_pages/6_Settings.py",
    "TEST": "app_pages/X_Tests.py",
}


def setup_logging():
    """Configure application logging."""
    log_level = os.environ.get("LOG_LEVEL", "DEBUG").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.DEBUG),
        format="%(asctime)s - %(levelname)s - %(name)s - %(pathname)s:%(lineno)d - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Silence noisy third-party loggers
    logging.getLogger("watchdog").setLevel(logging.WARNING)
    return logging.getLogger(__name__)


def init_config():
    """Initialize application configuration."""
    config = cfg()
    try:
        config.read_config()
    except FileNotFoundError:
        st.error(
            "Settings file not found. Please verify your configuration file exists and is accessible."
        )
        st.stop()
    return config


def setup_navigation():
    """Configure application navigation structure."""
    pages = {
        "home": st.Page(APP_PAGES["HOME"], title="Home", icon="🏠", default=True),
        "portfolios": st.Page(APP_PAGES["PORTFOLIOS"], title="Portfolios", icon="💰"),
        "graphs": st.Page(APP_PAGES["GRAPHS"], title="Graphs", icon="📊"),
        "operations": st.Page(APP_PAGES["OPERATIONS"], title="Operations", icon="💱"),
        "import": st.Page(APP_PAGES["IMPORT"], title="Import", icon="📥"),
        "token_metadata": st.Page(
            APP_PAGES["TOKEN_METADATA"], title="Token Metadata", icon="🏷️"
        ),
        "settings": st.Page(APP_PAGES["SETTINGS"], title="Settings", icon="⚙️"),
        "tests": st.Page(APP_PAGES["TEST"], title="Tests", icon="🧪"),
    }

    return st.navigation(
        {
            "Main": [pages["home"], pages["portfolios"], pages["graphs"]],
            "Tools": [pages["operations"], pages["import"], pages["token_metadata"]],
            "Settings": [pages["settings"]],
            "Dev": [pages["tests"]],
        }
    )


def main():
    """Main application entry point."""
    # Setup application
    logger = setup_logging()
    logger.debug("### Start Render ###")

    # Configure Streamlit page
    st.set_page_config(layout="wide", page_title="CryptoUpdate", page_icon="📈")

    # Initialize configuration
    config = init_config()
    tools.load_settings(config.conf)

    # Apply pending database migrations (once per session)
    if "db_migrations_applied" not in st.session_state:
        from modules.database.migrations import run_migrations

        run_migrations(st.session_state.settings["dbfile"])
        st.session_state["db_migrations_applied"] = True

    # Setup and run navigation
    navigator = setup_navigation()
    navigator.run()

    # Debug information
    if st.session_state.settings["debug_flag"]:
        st.write("Debug mode is ON")
        # Filter out sensitive data from session state before displaying
        safe_session_state = {
            k: v
            for k, v in st.session_state.items()
            if k not in ["settings"] and not k.endswith("_token")
        }
        # Add non-sensitive settings
        if "settings" in st.session_state:
            safe_session_state["settings"] = {
                k: (
                    "***REDACTED***"
                    if "token" in k.lower() or "password" in k.lower()
                    else v
                )
                for k, v in st.session_state.settings.items()
            }
        st.write(safe_session_state)

    logger.debug("### End Render ###")


if __name__ == "__main__":
    main()
