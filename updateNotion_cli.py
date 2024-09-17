import configparser
import logging
import typer
from enum import Enum
from modules.Exporter import Exporter
from modules.Notion import Notion
from modules.Updater import Updater

#logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def updateNotion(inifile: str):
 
    config = configparser.ConfigParser()
    config.read(inifile)

    try:
        #read config
        notion_api_token = config["DEFAULT"]["notion_token"]
        coinmarketcap_api_token = config["DEFAULT"]["coinmarketcap_token"]
        database = config["Notion"]["database"]
        parent_page = config["Notion"]["parent_page"]
        debug = (True if config["DEFAULT"]["debug"] == "True" else False)

    except KeyError as ke:
        logging.error("Error: " + type(ke).__name__ + " - " + str(ke))
        logging.error("Please set your settings in the settings file")
        quit()

    notion = Notion(notion_api_token)
    db_id = notion.getObjectId(database, "database", parent_page)
    if db_id == None:
        logging.error("Error: Database not found")
        quit()
            
    #update database with current market values
    Updater(coinmarketcap_api_token, notion_api_token, db_id).UpdateCrypto(debug=debug)

    #export database to file. 
    # destination: ./archives/[epoch]/*.csv
    file = Exporter(notion_api_token).GetCSVfile(database)

    logging.info(f"Output file: {file}")
    logging.info("Done.")

if __name__ == "__main__":
    typer.run(updateNotion)
