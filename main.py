from dotenv import load_dotenv
from modules import Exporter, Updater

if __name__ == "__main__":
    load_dotenv()

    #update database with current market values
    Updater.Updater().UpdateCrypto()

    #export database to csv file. 
    # destination: ./archives/[epoch]/*.csv
    csvfile = Exporter.Exporter().GetCSVfile()
    print("Output file: ", csvfile)

    print("Done.")
