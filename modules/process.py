import pandas as pd
import logging

logger = logging.getLogger(__name__)

def dropDuplicate(conn):
    try:
        df = pd.read_sql_query("SELECT * from Database;", conn)
    except:
        logger.debug("Database is empty. Skipping...")
        return 
    dupcount = df.duplicated().sum()
    logger.debug(f"Found {len(df)} rows with {dupcount} duplicated rows")
    if dupcount > 0:
        logger.debug(f"Found {dupcount} duplicated rows. Dropping...") 
        df.drop_duplicates(inplace=True)
        df.to_sql('Database', conn, if_exists='replace', index=False)

def getDateFrame(inputfile):
    logger.debug(f"Reading {inputfile}")
    df = pd.read_csv(inputfile)
    df.fillna(0, inplace=True)
    dftemp = df[["Token","Price/Coin","Coins in wallet", "Timestamp"]]
    dftemp.columns = ["token","price","count", "timestamp"]
    dfret = dftemp.copy()
    logger.debug(f"Found {len(dfret)} rows")
    return dfret