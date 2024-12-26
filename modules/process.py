import pandas as pd
import logging
import os
import hashlib
import streamlit as st
from modules.database.historybase import HistoryBase as hb

logger = logging.getLogger(__name__)

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
    # Récupérer la valeur brute 
    try:
        histbd = hb(st.session_state.dbfile)
        raw_price = histbd.get_last_price(token)
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
    
def debug_prefix(input : str, flag = False) -> str:
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
 
    st.session_state.archive_path = os.path.join(os.getcwd(), debug_prefix(settings["Local"]["archive_path"], st.session_state.settings["debug_flag"]))
    st.session_state.data_path = os.path.join(os.getcwd(), settings["Local"]["data_path"])
    st.session_state.dbfile = os.path.join(st.session_state.data_path, debug_prefix(settings["Local"]["sqlite_file"], st.session_state.settings["debug_flag"]))

def get_file_hash(filename):
    """Calculate MD5 hash of file"""
    md5_hash = hashlib.md5()
    with open(filename, "rb") as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

# load database
@st.cache_data(
    show_spinner=False,
    hash_funcs={str: lambda x: get_file_hash(x) if os.path.isfile(x) else hash(x)}
)
def load_db(dbfile: str) -> pd.DataFrame:
    with st.spinner("Loading database..."):
        logger.debug("Load database")
        histdb = hb(dbfile)
        df_balance = histdb.getBalances()
        df_sums = histdb.getSums()
        df_market = histdb.getMarket()
        df_tokencount = histdb.getTokenCounts()
        return df_balance, df_sums, df_market, df_tokencount
    