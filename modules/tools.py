"""Utility functions module for CryptoUpdate application.

This module provides various utility functions for:
- Database operations and updates
- Data frame manipulations
- Settings management
- Price calculations and interpolations
"""

import logging
import os

import pandas as pd
import streamlit as st

from modules.database.market import Market
from modules.database.portfolios import Portfolios
from modules.database.tokensdb import TokensDatabase
from modules.utils import debug_prefix, get_file_hash, interpolate

logger = logging.getLogger(__name__)


def update_database(dbfile, cmc_apikey):
    """Update the database with the latest market data"""
    market = Market(dbfile, cmc_apikey)
    portfolio = Portfolios(dbfile)

    aggregated = portfolio.aggregate_portfolios()
    if len(aggregated) == 0:
        logger.warning("No data found in portfolios")
        tokens = []
    else:
        tokens = list(aggregated.keys())
        logger.debug("Tokens: %s", str(tokens))

    market.updateMarket(tokens)
    market.updateCurrencies()

    tokens_prices = market.getLastMarket()
    if tokens_prices is None:
        logger.error("No Market data available")
        return None

    new_entries = {}
    for token in tokens:
        new_entries[token] = {
            "amount": aggregated[token],
            "price": tokens_prices.loc[token]["value"],
            "timestamp": tokens_prices.loc[token]["timestamp"],
        }
    TokensDatabase(dbfile).addTokens(new_entries)


def create_portfolio_dataframe(data: dict) -> pd.DataFrame:
    """Create a dataframe from the portfolio data"""
    logger.debug("Create portfolio dataframe - Data: %s", str(data))
    if not data:
        logger.debug("No data")
        return pd.DataFrame()
    df = pd.DataFrame.from_dict(data, columns=["amount"], orient="index")
    df["amount"] = df["amount"].astype(float)
    df.index.name = "token"
    logger.debug("Create portfolio dataframe - Dataframe:\n%s", df.to_string())
    market = Market(
        st.session_state.dbfile, st.session_state.settings["coinmarketcap_token"]
    )
    df["value(€)"] = df.apply(
        lambda row: row["amount"] * market.get_price(row.name),
        axis=1,
    )
    # sort df by token
    df = df.sort_index()
    return df


def get_dataframe(inputfile: str) -> pd.DataFrame:
    """Read the input file and return a dataframe"""
    logger.debug("Reading %s", inputfile)
    df = pd.read_csv(inputfile)
    df.fillna(0, inplace=True)
    dftemp = df[["Token", "Market Price", "Coins in wallet", "Timestamp"]]
    dftemp.columns = ["token", "price", "count", "timestamp"]
    dfret = dftemp.copy()
    logger.debug("Found %d rows", len(dfret))
    return dfret


def load_settings(settings: dict):
    """Load the settings from the configuration file"""
    logger.debug("Loading settings")
    if "settings" not in st.session_state:
        st.session_state.settings = {}
    st.session_state.settings["notion_token"] = settings["Notion"]["token"]
    st.session_state.settings["notion_database"] = settings["Notion"]["database"]
    st.session_state.settings["notion_parentpage"] = settings["Notion"]["parentpage"]
    st.session_state.settings["coinmarketcap_token"] = settings["Coinmarketcap"][
        "token"
    ]
    st.session_state.settings["openai_token"] = settings["OpenAI"]["token"]
    st.session_state.settings["debug_flag"] = (
        True if settings["Debug"]["flag"] == "True" else False
    )

    st.session_state.archive_path = os.path.join(
        os.getcwd(),
        debug_prefix(
            settings["Local"]["archive_path"], st.session_state.settings["debug_flag"]
        ),
    )
    st.session_state.data_path = os.path.join(
        os.getcwd(), settings["Local"]["data_path"]
    )
    st.session_state.dbfile = os.path.join(
        st.session_state.data_path,
        debug_prefix(
            settings["Local"]["sqlite_file"], st.session_state.settings["debug_flag"]
        ),
    )


# load database
@st.cache_data(
    show_spinner=False,
    hash_funcs={str: lambda x: get_file_hash(x) if os.path.isfile(x) else hash(x)},
)
def load_db(dbfile: str) -> pd.DataFrame:
    """Load the database"""
    with st.spinner("Loading database..."):
        logger.debug("Load database")
        tokensdb = TokensDatabase(dbfile)
        df_balance = tokensdb.getBalances()
        df_sums = tokensdb.getSums()
        df_tokencount = tokensdb.getTokenCounts()
        return df_balance, df_sums, df_tokencount


def interpolate_token(token: str, timestamp: int, dbfile: str) -> float:
    """Interpolate the token value at a given timestamp"""
    
    market = Market(dbfile, st.session_state.settings["coinmarketcap_token"])
    if token == "EURUSD":
        df_low, df_high = market.get_currency_lowhigh(timestamp)
    else:
        df_low, df_high = market.get_token_lowhigh(token, timestamp)

    if len(df_low) == 0:
        logger.warning(
            "Interpolate token - No data found for token: %s and timestamp: %d",
            token,
            timestamp,
        )
        return None
    if len(df_high) == 0:
        logger.debug(
            "Interpolate token - No high data found for token: %s and timestamp: %d - using low data",
            token,
            timestamp
        )
        df_high = df_low.copy()

    # Interpoler la valeur
    price_low = df_low["price"][0]
    price_high = df_high["price"][0]
    timestamp_low = df_low["timestamp"][0]
    timestamp_high = df_high["timestamp"][0]
    price = interpolate(
        timestamp_low, price_low, timestamp_high, price_high, timestamp
    )
    logger.debug("Interpolate token - Price: %f", price)
    return price

def interpolate_eurusd(timestamp: int, dbfile: str) -> float:
    """Interpolate the EURUSD value at a given timestamp"""
    return interpolate_token("EURUSD", timestamp, dbfile)

def calculate_crypto_rate(token_a: str, token_b: str, timestamp: int, dbfile: str) -> float:
    """Calculate the rate between two cryptocurrencies at a given timestamp"""
    logger.debug(
        "Calculate crypto rate - Token A: %s - Token B: %s - Timestamp: %d",
        token_a,
        token_b,
        timestamp,
    )

    value_a = interpolate_token(token_a, timestamp, dbfile)
    value_b = interpolate_token(token_b, timestamp, dbfile)
    if value_a is None or value_b is None:
        return None
    rate = value_a / value_b
    logger.debug("Calculate crypto rate - 1 %s = %f %s", token_a, rate, token_b)
    return rate
