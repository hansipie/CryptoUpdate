import os
import configparser
from modules import Exporter, Updater

if __name__ == "__main__":
    #read config
    config = configparser.ConfigParser()
    config.read('./data/settings.ini')


    #update database with current market values
    Updater.Updater(config["DEFAULT"]["coinmarketcap_token"], config["DEFAULT"]["notion_token"]).UpdateCrypto()

    #export database to csv file. 
    # destination: ./archives/[epoch]/*.csv
    csvfile = Exporter.Exporter(config["DEFAULT"]["notion_token"]).GetCSVfile()
    print("Output file: ", csvfile)

    print("Done.")
