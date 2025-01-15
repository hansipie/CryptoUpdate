import sqlite3
import pandas as pd
import logging
import os
import streamlit as st
from modules.database.historybase import HistoryBase as hb
from modules.utils import clean_price, debug_prefix, get_file_hash

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
        df_tokencount = histdb.getTokenCounts()
        return df_balance, df_sums, df_tokencount
    
def interpolate_EURUSD(timestamp: int, dbfile: str) -> float:
    with sqlite3.connect(dbfile) as con:
        df_low = pd.read_sql_query(
            f"SELECT timestamp, price from Currency WHERE timestamp <= {timestamp} ORDER BY timestamp DESC LIMIT 1;",
            con,
        )
        df_high = pd.read_sql_query(
            f"SELECT timestamp, price from Currency WHERE timestamp >= {timestamp} ORDER BY timestamp ASC LIMIT 1;",
            con,
        )
        if len(df_high) == 0:
            logger.debug(st.session_state.settings["currencyapi_token"])
            client = currencyapicom.Client(st.session_state.settings["currencyapi_token"])
            result = client.latest()
            logger.debug(f"Extrapolate EURUSD - API result: {result}")

        logger.debug(f"Extrapolate EURUSD - timestamp: {timestamp}\n- low:\n{df_low}\n- high:\n{df_high}")
        if len(df_low) == 0 or len(df_high) == 0:
            logger.warning(f"Extrapolate EURUSD - No data found for timestamp: {timestamp}")
            return 0.0
        else:
            # Interpoler la valeur
            price_low = df_low["price"][0]
            price_high = df_high["price"][0]
            timestamp_low = df_low["timestamp"][0]
            timestamp_high = df_high["timestamp"][0]
            price = price_low + (price_high - price_low) * (timestamp - timestamp_low) / (timestamp_high - timestamp_low)
            logger.debug(f"Extrapolate EURUSD - Price: {price}")
            return price
    
    
