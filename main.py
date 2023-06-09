import sys
import Exporter
import Updater
import os

#update database with current market values
if "cli" in sys.argv :
    print("CLI mode")
    Updater.Updater().UpdateCrypto()
else:
    print("Silent mode")
    Updater.Updater().UpdateCryptoSilent()

#export database to csv file. 
# destination: ./archives/[epoch]/*.csv
csvdir = Exporter.Exporter().GetCSVfile()
files=os.listdir(csvdir)

for f in files:
    print("Output file: ", f)
    
print("Done.")
