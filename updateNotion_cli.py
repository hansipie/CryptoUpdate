import os
import configparser
from modules.Exporter import Exporter
from modules.Notion import Notion
from modules.Updater import Updater

if __name__ == "__main__":

    config = configparser.ConfigParser()
    config.read('./data/settings.ini')

    try:
        #read config
        notion_api_token = config["DEFAULT"]["notion_token"]
        coinmarketcap_api_token = config["DEFAULT"]["coinmarketcap_token"]
        database = config["Notion"]["database"]
        parent_page = config["Notion"]["parent_page"]

    except KeyError as ke:
        print("Error: " + type(ke).__name__ + " - " + str(ke))
        print("Please set your settings in the settings file")
        quit()

    notion = Notion(notion_api_token)
    db_id = notion.getObjectId(database, "database", parent_page)
    if db_id == None:
        print("Error: Database not found")
        quit()
            
    #update database with current market values
    Updater(coinmarketcap_api_token, notion_api_token, db_id).UpdateCrypto()

    #export database to csv file. 
    # destination: ./archives/[epoch]/*.csv
    csvfile = Exporter(notion_api_token).GetCSVfile(database)
    print("Output file: ", csvfile)
    print("Done.")

