import os
import sqlite3
import logging
import typer
import csv
import configparser
import logging
import typer

from modules.Exporter import Exporter
from modules.Notion import Notion
from modules.Updater import Updater
from alive_progress import alive_bar
from modules import tools
from modules.database.historybase import HistoryBase
from modules.utils import debug_prefix, listfilesrecursive

# logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = typer.Typer()

@app.command()
def addTimestamps(inifile: str):
    """
    Reads a configuration file to get the directory path, iterates through all subdirectories,
    and adds a "Timestamp" column to each [CSV file](https://en.wikipedia.org/wiki/Comma-separated_values) with the value of the current timestamp.

    Args:
        inifile (str): Path to the configuration file.

    Raises:
        KeyError: If the required configuration settings are not found in the configuration file.
    """

    config = configparser.ConfigParser()
    config.read(inifile)

    try:
        # Read config
        directory = os.path.join(os.getcwd(), config["Local"]["archive_path"])
    except KeyError as ke:
        logging.error("Error: " + type(ke).__name__ + " - " + str(ke))
        logging.error("Please set your settings in the settings file")
        quit()

    listdirs = list(filter(lambda x : os.path.isdir(os.path.join(directory, x)), os.listdir(directory)))
    count = len(listdirs)
    with alive_bar(
        count, title="Add timestamp", force_tty=True, stats="(eta:{eta})"
    ) as bar:
        for timestamp in listdirs:
            if os.path.isdir(os.path.join(os.getcwd(), directory, timestamp)):
                logger.debug(f"Processing directory: {timestamp}")
                for filename in os.listdir(os.path.join(directory, timestamp)):
                    if filename.endswith(".csv"):
                        filepath = os.path.join(directory, timestamp, filename)
                        # Open file and add a new column to the CSV file with the name "Timestamp" and the value of the current timestamp
                        with open(filepath, mode="r", encoding="utf-8-sig") as csvfile:
                            reader = csv.reader(csvfile)
                            rows = list(reader)
                        # Check if row timestamp already exists
                        if "Timestamp" in rows[0]:
                            logger.debug(f"Timestamp already exists in file: {filepath}")
                            continue
                        # Else add timestamp to the first row and the value to the rest of the rows
                        with open(filepath, mode="w", encoding="utf-8-sig", newline="") as csvfile:
                            writer = csv.writer(csvfile)
                            writer.writerow(rows[0] + ["Timestamp"])
                            for row in rows[1:]:
                                writer.writerow(row + [timestamp])
                        logger.debug(f"Added timestamp to file: {filepath}")
                        # Move file to ../{epoch}.csv
            bar()

@app.command()
def saveToDB(inifile):
    """
    Reads configuration from an ini file, processes CSV files from a specified archive directory,
    and saves the data into a [SQLite](https://www.sqlite.org/index.html) database.

    Args:
        inifile (str): Path to the ini configuration file.

    Raises:
        KeyError: If required configuration keys are missing in the ini file.
    """

    config = configparser.ConfigParser()
    config.read(inifile)

    try:
        # Read config
        debug_flag = True if config["Debug"]["flag"] == "True" else False
        archive_path = os.path.join(os.getcwd(), debug_prefix(config["Local"]["archive_path"], debug_flag))
        data_path = os.path.join(os.getcwd(), config["Local"]["data_path"])
        dbfile = os.path.join(data_path, debug_prefix(config["Local"]["sqlite_file"], debug_flag))

    except KeyError as ke:
        logging.error("Error: " + type(ke).__name__ + " - " + str(ke))
        logging.error("Please set your settings in the settings file")
        quit()

    conn = sqlite3.connect(dbfile)

    archiveFiles = listfilesrecursive(archive_path)
    count = len(archiveFiles)
    with alive_bar(
        count, title="Insert in database", force_tty=True, stats="(eta:{eta})"
    ) as bar:
        for item in archiveFiles:
            if item.endswith(".csv"):
                df = tools.getDateFrame(item)
                df.to_sql("Database", conn, if_exists="append", index=False)
            else:
                logger.debug(f"ignore: {item}")
            bar()
    conn.close()

    histdb = HistoryBase(dbfile)
    histdb.dropDuplicate()

@app.command()
def updateNotion(inifile: str):
    """
    Updates a Notion database with current market values and exports the database to a CSV file.

    Args:
        inifile (str): Path to the configuration file.

    The configuration file should contain the following sections and keys:
        [Notion]
        token = <your_notion_api_token>
        database = <your_database_name>
        parentpage = <your_parent_page_id>

        [Coinmarketcap]
        token = <your_coinmarketcap_api_token>

        [Local]
        archive_path = <path_to_archive_directory>

        [Debug]
        flag = <True/False>
    """

    config = configparser.ConfigParser()
    config.read(inifile)

    try:
        # read config
        notion_api_token = config["Notion"]["token"]
        coinmarketcap_api_token = config["Coinmarketcap"]["token"]
        database = config["Notion"]["database"]
        parentpage = config["Notion"]["parentpage"]
        archive_path = os.path.join(os.getcwd(), config["Local"]["archive_path"])

    except KeyError as ke:
        logging.error("Error: " + type(ke).__name__ + " - " + str(ke))
        logging.error("Please set your settings in the settings file")
        quit()

    notion = Notion(notion_api_token)
    db_id = notion.getObjectId(database, "database", parentpage)
    if db_id == None:
        logging.error("Error: Database not found")
        quit()

    # update database with current market values
    Updater(coinmarketcap_api_token, notion_api_token, db_id).UpdateCrypto()

    # export database to file.
    # destination: {archive_path}/[epoch]/*.csv
    file = Exporter(notion_api_token, archive_path).GetCSVfile(database, parentpage)

    logging.info(f"Output file: {file}")
    logging.info("Done.")

@app.command()
def redwire(inifile: str):
    """
    Executes a series of operations.

    This function performs the following steps:
    1. Updates Notion.
    2. Adds timestamps.
    3. Saves to the database.

    Args:
        inifile (str): The path to the ini file to be processed.
    """
    logger.info("/************ Updates Notion *************/")
    updateNotion(inifile)
    logger.info("/************ Adds timestamps *************/")
    addTimestamps(inifile)
    logger.info("/************ Saves to the database *************/")
    saveToDB(inifile)

if __name__ == "__main__":
    app()
