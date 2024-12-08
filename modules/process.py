import pandas as pd
import logging
import os
import streamlit as st

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

def listfilesrecursive(directory, fileslist=None):
    # list all files in directory recurcively

    if fileslist is None:
        fileslist = []

    items = os.listdir(directory)
    #logger.debug(f"list directory {directory}: {items}")
    for item in items:
        path = os.path.join(directory, item)
        if os.path.isdir(path):
            #logger.debug(f"{path} is a directory.")
            listfilesrecursive(path, fileslist)
        else:
            #logger.debug(f"Add file {path}")
            fileslist.append(path)
    #logger.debug(f"Return {fileslist}")
    return fileslist

def clean_price(price: str) -> float:
    cleaned_price = str(price).replace("$", "").replace("€", "").replace(",", ".").replace(" ", "")
    return float(cleaned_price)


def get_current_price(token: str) -> float:
    prices = st.session_state.database["market"].tail(1)
    if prices.empty:
        return 0.0

    # Récupérer la valeur brute
    raw_price = prices[token].values[0]

    # Nettoyer et convertir la valeur
    try:
        # Supprimer les caractères non numériques et convertir en float
        price = clean_price(raw_price)
        logger.debug(f"get_current_price - Token: {token} - Price: {price}")
        return price
    except (ValueError, TypeError):
        logger.warning(f"Impossible de convertir le prix pour {token}: {raw_price}")
        return 0.0