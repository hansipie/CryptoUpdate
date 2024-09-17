import os
import shutil
import sqlite3
import pandas as pd
from alive_progress import alive_bar
from modules import process
import logging
import typer
import csv

#logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = typer.Typer()

def __listfilesrecursive(directory, fileslist = None):
    # list all files in directory recurcively

    if fileslist is None:
        fileslist = []

    items = os.listdir(directory)
    logger.debug(f"list directory {directory}: {items}")
    for item in items:
        path = os.path.join(directory, item)
        if os.path.isdir(path):
            logger.debug(f"{path} is a directory.")
            __listfilesrecursive(path, fileslist)
        else:
            logger.debug(f"Add file {path}")
            fileslist.append(path)
    logger.debug(f"Return {fileslist}")
    return fileslist

@app.command()
def addTimestamps(directory):
    for timestamp in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, timestamp)):
            logger.info(f"Processing directory: {timestamp}")
            for filename in os.listdir(os.path.join(directory, timestamp)):
                if filename.endswith(".csv"):
                    filepath = os.path.join(directory, timestamp, filename)
                    # open file and add a new column to the CSV file with the name "Timestamp" and the value of the current timestamp
                    with open(filepath, mode="r", encoding="utf-8-sig") as csvfile:
                        reader = csv.reader(csvfile)
                        rows = list(reader)
                    #check if row timsstamp already exists
                    if "Timestamp" in rows[0]:
                        logger.info(f"Timestamp already exists in file: {filepath}")
                        continue
                    # else add timestamp to the first row and the value to the rest of the rows
                    with open(filepath, mode="w", encoding="utf-8-sig", newline="") as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(rows[0] + ["Timestamp"])
                        for row in rows[1:]:
                            writer.writerow(row + [timestamp])
                    logger.info(f"Added timestamp to file: {filepath}")
                    # move file to ../{epoch}.csv
                    
@app.command()
def saveToDB():

    dbfile = "./data/db.sqlite3"
    conn = sqlite3.connect(dbfile)

    archivedir = "./archives/"
    archiveFiles = __listfilesrecursive(archivedir)
    count = len(archiveFiles)
    with alive_bar(count, title='Migrate archives dirs', force_tty=True, stats='(eta:{eta})') as bar:
        for item in archiveFiles:
            if item.endswith(".csv"):
                df = process.getDateFrame(item)
                df.to_sql('Database', conn, if_exists='append', index=False)
            else:
                logger.debug(f"ignore: {item}")
            bar()
    process.dropDuplicate(conn)
    conn.close()

if __name__ == "__main__":
    app()