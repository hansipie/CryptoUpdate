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
    dftemp = df[["Token","Market Price","Coins in wallet", "Timestamp"]]
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
    logger.debug(f"Clean price: {price}")
    cleaned_price = str(price).replace("$", "").replace("€", "").replace(",", ".").replace(" ", "")
    return float(cleaned_price)


def get_current_price(token: str) -> float:
    prices = st.session_state.database["market"].tail(1)
    if prices.empty:
        return 0.0

    # Récupérer la valeur brute 
    try:
        raw_price = prices[token].values[0]
    except KeyError:
        logger.warning(f"Pas de prix pour {token}")
        return 0.0

    # Nettoyer et convertir la valeur
    try:
        # Supprimer les caractères non numériques et convertir en float
        price = clean_price(raw_price)
        logger.debug(f"get_current_price - Token: {token} - Price: {price}")
        return price
    except (ValueError, TypeError):
        logger.warning(f"Impossible de convertir le prix pour {token}: {raw_price}")
        return 0.0
    
def prefix(input : str, flag = False) -> str:
    if flag:
        return f"debug_{input}"
    return input

def loadSettings(settings: dict):
    logger.debug("Loading settings")
    if "settings" not in st.session_state:
        st.session_state.settings = {}
    st.session_state.settings["notion_token"] = settings["Notion"]["token"]
    st.session_state.settings["notion_database"] = settings["Notion"]["database"]
    st.session_state.settings["notion_parentpage"] = settings["Notion"]["parentpage"]
    st.session_state.settings["coinmarketcap_token"] = settings["Coinmarketcap"]["token"]
    st.session_state.settings["openai_token"] = settings["OpenAI"]["token"]
    st.session_state.settings["debug_flag"] = True if settings["Debug"]["flag"] == "True" else False
 
    st.session_state.archive_path = os.path.join(os.getcwd(), prefix(settings["Local"]["archive_path"], st.session_state.settings["debug_flag"]))
    st.session_state.data_path = os.path.join(os.getcwd(), settings["Local"]["data_path"])
    st.session_state.dbfile = os.path.join(st.session_state.data_path, prefix(settings["Local"]["sqlite_file"], st.session_state.settings["debug_flag"]))
