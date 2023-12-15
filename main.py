import sys
import Exporter
import Updater
import os
from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv()

    #update database with current market values
    if "cli" in sys.argv :
        print("CLI mode")
        Updater.Updater().UpdateCrypto()
    else:
        print("Silent mode")
        Updater.Updater().UpdateCryptoSilent()

    #export database to csv file. 
    # destination: ./archives/[epoch]/*.csv
    csvfile = Exporter.Exporter().GetCSVfile()
    print("Output file: ", csvfile)

    print("Done.")
