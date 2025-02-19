"""Main entry point for CryptoUpdate application.

This module initializes the Streamlit application, sets up logging,
loads configuration and defines the navigation structure.
The application provides a web interface for tracking and managing
cryptocurrency portfolios.
"""

# Standard library imports
import logging
import sys

# Third-party imports
import streamlit as st

# Local imports
from modules import tools
from modules.configuration import configuration as cfg

# Application constants
APP_PAGES = {
    "HOME": "app_pages/0_Home.py",
    "PORTFOLIOS": "app_pages/1_Portfolios.py",
    "GRAPHS": "app_pages/2_Graphs.py",
    "OPERATIONS": "app_pages/3_Operations.py",
    "IMPORT": "app_pages/4_Import.py",
    "SETTINGS": "app_pages/6_Settings.py",
    "TEST": "app_pages/X_Tests.py",
}


def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(name)s - %(pathname)s:%(lineno)d - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger(__name__)


def init_config():
    """Initialize application configuration."""
    config = cfg()
    try:
        config.readConfig()
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
        "portfolios": st.Page(APP_PAGES["PORTFOLIOS"], title="Portfolios", icon="📊"),
        "graphs": st.Page(APP_PAGES["GRAPHS"], title="Graphs", icon="💰"),
        "operations": st.Page(APP_PAGES["OPERATIONS"], title="Operations", icon="💱"),
        "import": st.Page(APP_PAGES["IMPORT"], title="Import", icon="📥"),
        "settings": st.Page(APP_PAGES["SETTINGS"], title="Settings", icon="⚙️"),
        "tests": st.Page(APP_PAGES["TEST"], title="Tests", icon="🧪"),
    }

    return st.navigation(
        {
            "Main": [pages["home"], pages["portfolios"], pages["graphs"]],
            "Tools": [pages["operations"], pages["import"]],
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

    # Setup and run navigation
    navigator = setup_navigation()
    navigator.run()

    # Debug information
    if st.session_state.settings["debug_flag"]:
        st.write("Debug mode is ON")
        st.write(st.session_state)

    logger.debug("### End Render ###")


if __name__ == "__main__":
    main()
