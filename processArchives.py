import os
import shutil
import sqlite3
import pandas as pd
from alive_progress import alive_bar

def dropDuplicate(conn):
    df = pd.read_sql_query("SELECT * from Database;", conn)
    dupcount = df.duplicated().sum()
    if dupcount > 0:
        print(f"Found {dupcount} duplicated rows. Dropping...") 
        df.drop_duplicates(inplace=True)
        df.to_sql('Database', conn, if_exists='replace', index=False)


def getDateFrame(inputfile, epoch):
    df = pd.read_csv(inputfile)
    df.fillna(0, inplace=True)
    dftemp = df[["Token","Price/Coin","Coins in wallet"]]
    dftemp.columns = ["token","price","count"]
    dfret = dftemp.copy()
    dfret['timestamp'] = epoch
    return dfret

if __name__ == "__main__":

    dbfile = "./outputs/db.sqlite3"
    conn = sqlite3.connect(dbfile)

    archivedir = "./archives/"
    count = len(os.listdir(archivedir))
    with alive_bar(count, title='Migrate archives', force_tty=True, stats='(eta:{eta})') as bar:
        for folder in os.listdir(archivedir):
            if folder.isnumeric():
                epoch = int(folder)
                forderpath = os.path.join(archivedir, folder)
                for file in os.listdir(forderpath):
                    if file.endswith("_all.csv"):
                        continue
                    if file.endswith(".csv"):
                        inputfile = os.path.join(forderpath, file)
                        df = getDateFrame(inputfile, epoch)
                        df.to_sql('Database', conn, if_exists='append', index=False)
            bar()
    with alive_bar(count, title='Delete archives', force_tty=True, stats='(eta:{eta})') as bar:
        for folder in os.listdir(archivedir):
            forderpath = os.path.join(archivedir, folder)
            if os.path.isdir(forderpath):
                shutil.rmtree(forderpath, ignore_errors=True)
            bar()

    dropDuplicate(conn)
    conn.close()
