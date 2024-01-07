import os
from dotenv import load_dotenv
from modules import Exporter, Updater

if __name__ == "__main__":
    load_dotenv()

    if os.getenv('MY_COINMARKETCAP_APIKEY') is None:
        print("Please set your Coinmarketcap API key in the .env file")
        quit()
    if os.getenv('NOTION_API_TOKEN') is None:
        print("Please set your Notion API key in the .env file")
        quit()

    #update database with current market values
    Updater.Updater().UpdateCrypto()

    #export database to csv file. 
    # destination: ./archives/[epoch]/*.csv
    csvfile = Exporter.Exporter().GetCSVfile()
    print("Output file: ", csvfile)

    print("Done.")
