import os
import shutil
import sqlite3
import pandas as pd
from alive_progress import alive_bar
from modules import process
import logging

#logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":

    dbfile = "./data/db.sqlite3"
    conn = sqlite3.connect(dbfile)

    archivedir = "./archives/"
    # lambda function to filter archivedir to only folders
    archivedirs = list(filter(lambda x: os.path.isdir(os.path.join(archivedir, x)), os.listdir(archivedir)))
    count = len(archivedirs)
    if count == 0:
        logging.error("No archives found. Exiting...")
        exit()
    with alive_bar(count, title='Migrate archives', force_tty=True, stats='(eta:{eta})') as bar:
        for folder in archivedirs:
            if folder.isnumeric():
                epoch = int(folder)
                forderpath = os.path.join(archivedir, folder)
                for file in os.listdir(forderpath):
                    if file.endswith("_all.csv"):
                        continue
                    if file.endswith(".csv"):
                        inputfile = os.path.join(forderpath, file)
                        df = process.getDateFrame(inputfile, epoch)
                        df.to_sql('Database', conn, if_exists='append', index=False)
            bar()
    with alive_bar(count, title='Delete archives', force_tty=True, stats='(eta:{eta})') as bar:
        for folder in archivedirs:
            forderpath = os.path.join(archivedir, folder)
            if os.path.isdir(forderpath):
                shutil.rmtree(forderpath, ignore_errors=True)
            bar()

    process.dropDuplicate(conn)
    conn.close()
