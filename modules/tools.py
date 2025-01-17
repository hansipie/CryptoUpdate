import sqlite3
import pandas as pd
import logging
import os
import streamlit as st
from modules.database.market import Market
from modules.database.portfolios import Portfolios
from modules.database.tokensdb import TokensDatabase
from modules.utils import clean_price, debug_prefix, get_file_hash
from modules.cmc import cmc

logger = logging.getLogger(__name__)

def UpdateDatabase(dbfile, cmc_apikey):
    market = Market(dbfile, cmc_apikey)
    portfolio = Portfolios(dbfile)

    aggregated = portfolio.aggregate_portfolios()
    if len(aggregated) == 0:
        logger.warning("No data found in portfolios")
        tokens = []
    else:
        logger.debug(f"Aggregated: {aggregated}")
        tokens = list(aggregated.keys())
        logger.debug(f"Tokens: {tokens}")

    market.updateMarket(tokens)
    market.updateCurrencies()

    tokens_prices = market.getLastMarket()
    if tokens_prices is None:
        logger.error("No Market data available")
        return None
    
    new_entries = {}
    for token in tokens:
        logger.debug(f"Token: {tokens_prices[token]}")
        new_entries[token] = {
            "amount": aggregated[token]["amount"],
            "price": tokens_prices[token][tokens_prices.index[0]],
            "timestamp": tokens_prices.index[0],
        }
    TokensDatabase(dbfile).addTokens(new_entries)

def create_portfolio_dataframe(data: dict) -> pd.DataFrame:
    logger.debug(f"Create portfolio dataframe - Data: {data}")
    if not data:
        logger.debug("No data")
        return pd.DataFrame()
    df = pd.DataFrame(data).T
    df.index.name = "token"
    df["amount"] = df.apply(lambda row: clean_price(row["amount"]), axis=1)
    # Ajouter une colonne "Value" basée sur le cours actuel
    df["value(€)"] = df.apply(
        lambda row: round(
            clean_price(row["amount"]) * get_current_price(row.name), 2
        ),
        axis=1,
    )
    #sort df by token
    df = df.sort_index()
    return df
    

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
        tokensdb = TokensDatabase(st.session_state.dbfile)
        raw_price = tokensdb.get_last_price(token)
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
        tokensdb = TokensDatabase(dbfile)
        df_balance = tokensdb.getBalances()
        df_sums = tokensdb.getSums()
        df_tokencount = tokensdb.getTokenCounts()
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
        if len(df_low) == 0:
            logger.warning(f"Interpolate EURUSD - No data found for timestamp: {timestamp}")
            return None
        if len(df_high) == 0:
            cmc_price = cmc(st.session_state.settings["coinmarketcap_token"])
            prices = cmc_price.getCurrentFiatPrices(["USD"], "EUR", 1, st.session_state.settings["debug_flag"])
            try:
                df_high = pd.DataFrame(prices["USD"], index=[0])
            except KeyError:
                logger.warning(f"Interpolate EURUSD - No data found for timestamp: {timestamp}")
                return None
            if df_high["timestamp"][0] < timestamp:
                logger.warning(f"Interpolate EURUSD - No data found for timestamp: {timestamp}")
                return None

        logger.debug(f"Interpolate EURUSD - timestamp: {timestamp}\n- low:\n{df_low}\n- high:\n{df_high}")
        # Interpoler la valeur
        price_low = df_low["price"][0]
        price_high = df_high["price"][0]
        timestamp_low = df_low["timestamp"][0]
        timestamp_high = df_high["timestamp"][0]
        price = price_low + (price_high - price_low) * (timestamp - timestamp_low) / (timestamp_high - timestamp_low)
        logger.debug(f"Interpolate EURUSD - Price: {price}")
        return price
