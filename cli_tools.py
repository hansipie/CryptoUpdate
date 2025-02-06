import logging
import os
import typer

from modules.tools import update_database
from modules.configuration import configuration as cfg
from modules.utils import debug_prefix

# logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = typer.Typer()


@app.command()
def update_db(config_file: str = "./settings.json"):
    """Update the database with the latest market data"""

    config = cfg(config_file)
    try:
        config.readConfig()
    except FileNotFoundError as exc:
        logger.error(
            "Settings file not found. Please verify your configuration file exists and is accessible."
        )
        raise typer.Exit(code=1) from exc

    try:
        dbfile = os.path.join(
            os.getcwd(),
            config.conf["Local"]["data_path"],
            debug_prefix(
                config.conf["Local"]["sqlite_file"],
                config.conf["Debug"]["flag"] == "True",
            ),
        )
        logger.info("Database file: %s", dbfile)

        cmc_apikey = config.conf["Coinmarketcap"]["token"]
        logger.info("Coinmarketcap API key: %s", cmc_apikey)

        debug = config.conf["Debug"]["flag"]
        logger.info("Debug flag: %s", debug)
    except KeyError as exc:
        logger.error(
            "Missing configuration key. Please verify your configuration file is properly formatted."
        )
        raise typer.Exit(code=1) from exc

    logger.info("Updating database")
    try:
        update_database(dbfile, cmc_apikey, debug)
    except Exception as exc:
        logger.error("Error updating database: %s", str(exc))
        raise typer.Exit(code=1) from exc
    logger.info("Database updated")


if __name__ == "__main__":
    app()
