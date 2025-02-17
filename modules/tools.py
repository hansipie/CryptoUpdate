"""Utility functions module for CryptoUpdate application.

This module provides various utility functions for:
- Database operations and updates
- Data frame manipulations
- Settings management
- Price calculations and interpolations
"""

from datetime import datetime
import logging
import os
import shutil
import traceback
from typing import Union

import pandas as pd
import streamlit as st

from modules.database.customdata import Customdata
from modules.database.market import Market
from modules.database.portfolios import Portfolios
from modules.database.tokensdb import TokensDatabase
from modules.utils import debug_prefix, interpolate

logger = logging.getLogger(__name__)


def update_database(dbfile: str, cmc_apikey: str, debug: bool):
    """Update the database with the latest market data"""

    backup_database(dbfile)

    market = Market(dbfile, cmc_apikey)
    portfolio = Portfolios(dbfile)

    aggregated = portfolio.aggregate_portfolios()
    if len(aggregated) == 0:
        logger.info("No data available")
        tokens = []
    else:
        tokens = list(aggregated.keys())
        logger.debug("Tokens: %s", str(tokens))

    # remove EUR from tokens
    not_tokens = ["USD", "EUR"]
    tokens = [token for token in tokens if token not in not_tokens]
    logger.debug("Tokens after clean up: %s", str(tokens))

    try:
        market.update_market(tokens, debug=debug)
        market.update_currencies(debug=debug)
    except Exception as e:
        logger.error("Error updating market data: %s", str(e))
        traceback.print_exc()
        raise ValueError("Error updating market data") from e

    tokens_prices = market.getLastMarket()
    if tokens_prices is None:
        logger.error("No Market data available")
        raise ValueError("No Market data available")

    new_entries = {}
    for token in tokens:
        new_entries[token] = {
            "amount": aggregated[token],
            "price": tokens_prices.loc[token]["value"],
            "timestamp": tokens_prices.loc[token]["timestamp"],
        }
    TokensDatabase(dbfile).add_tokens(new_entries)

    custom = Customdata(dbfile)
    custom.set("last_update", str(pd.Timestamp.now(tz="UTC").timestamp()), "float")


def create_portfolio_dataframe(data: dict) -> pd.DataFrame:
    """Create a dataframe from the portfolio data"""
    logger.debug("Create portfolio dataframe - Data: %s", str(data))
    if not data:
        logger.debug("No data")
        return pd.DataFrame()
    df = pd.DataFrame.from_dict(data, columns=["amount"], orient="index")
    df["amount"] = df["amount"].astype(float)
    df.index.name = "token"
    logger.debug("Create portfolio dataframe - Dataframe:\n%s", df)
    market = Market(
        st.session_state.settings["dbfile"],
        st.session_state.settings["coinmarketcap_token"],
    )
    df["value(€)"] = df.apply(
        lambda row: row["amount"]
        * (market.get_price(row.name) if row.name != "EUR" else 1.0),
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
    st.session_state.settings["marketraccoon_url"] = settings["MarketRaccoon"]["url"]
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

    st.session_state.settings["archive_path"] = os.path.join(
        os.getcwd(),
        debug_prefix(
            settings["Local"]["archive_path"], st.session_state.settings["debug_flag"]
        ),
    )
    st.session_state.settings["data_path"] = os.path.join(
        os.getcwd(), settings["Local"]["data_path"]
    )
    st.session_state.settings["dbfile"] = os.path.join(
        st.session_state.settings["data_path"],
        debug_prefix(
            settings["Local"]["sqlite_file"], st.session_state.settings["debug_flag"]
        ),
    )


def __interpolater(
    df_low: pd.DataFrame, df_high: pd.DataFrame, timestamp: int, token: str = ""
) -> float:
    if len(df_low) == 0:
        logger.warning(
            "No data found for token: %s at timestamp: %d (%s)",
            token,
            timestamp,
            pd.Timestamp.fromtimestamp(int(timestamp), tz="UTC"),
        )
        return None
    if len(df_high) == 0:
        logger.debug(
            "No high data found for token: %s and timestamp: %d - using low data",
            token,
            timestamp,
        )
        df_high = df_low.copy()

    # Interpoler la valeur
    idxlow = df_low.first_valid_index()
    idxhigh = df_high.first_valid_index()
    if idxlow is None or idxhigh is None:
        raise ValueError("No valid index found")
    price_low = df_low["price"].loc[idxlow]
    price_high = df_high["price"].loc[idxhigh]
    timestamp_low = df_low["timestamp"].loc[idxlow]
    timestamp_high = df_high["timestamp"].loc[idxhigh]
    price = interpolate(timestamp_low, price_low, timestamp_high, price_high, timestamp)
    logger.debug("Price: %f", price)
    return price


def interpolate_token_b(token: str, timestamp: int, df: pd.DataFrame) -> float:
    """Interpolate the token value at a given timestamp from a dataframe"""
    logger.debug("Interpolate token - Token: %s - Timestamp: %d - from a dataframe", token, timestamp)
    if token == "EUR":
        return 1.0
    df_low = df[df["timestamp"] <= timestamp].iloc[-1:]
    df_high = df[df["timestamp"] >= timestamp].iloc[:1]

    return __interpolater(df_low, df_high, timestamp, token)


def interpolate_token(token: str, timestamp: int, dbfile: str) -> float:
    """Interpolate the token value at a given timestamp from the database"""
    logger.debug("Interpolate token - Token: %s - Timestamp: %d - from the database", token, timestamp)
    market = Market(dbfile, st.session_state.settings["coinmarketcap_token"])
    if token == "EUR":
        return 1.0
    if token == "EURUSD" or token == "USD":
        df_low, df_high = market.get_currency_lowhigh(timestamp)
    else:
        df_low, df_high = market.get_token_lowhigh(token, timestamp)

    return __interpolater(df_low, df_high, timestamp, token)


def interpolate_eurusd(timestamp: int, input_data: Union[str, pd.DataFrame]) -> float:
    """Interpolate the EURUSD value at a given timestamp"""
    if isinstance(input_data, str):
        return interpolate_token("EURUSD", timestamp, input_data)
    if isinstance(input_data, pd.DataFrame):
        return interpolate_token_b("EURUSD", timestamp, input_data)
    raise ValueError("Invalid input type")


def calculate_crypto_rate(
    token_a: str, token_b: str, timestamp: int, dbfile: str
) -> float:
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


def update():
    """Update cryptocurrency prices in database.

    Attempts to fetch latest prices and update the database.
    Shows success toast or error message on completion.
    """
    try:
        update_database(
            st.session_state.settings["dbfile"],
            st.session_state.settings["coinmarketcap_token"],
            st.session_state.settings["debug_flag"],
        )
        st.toast("Prices updated", icon=":material/check:")
        st.rerun()
    except (ConnectionError, ValueError) as e:
        st.error(f"Update Error: {str(e)}")
        traceback.print_exc()


def backup_database(dbfile: str) -> str:
    """Crée une sauvegarde du fichier de base de données en ajoutant un timestamp dans le nom.

    Args:
        dbfile: Chemin vers le fichier de base de données

    Returns:
        Chemin vers le fichier de sauvegarde créé

    Raises:
        FileNotFoundError: Si le fichier source n'existe pas
    """
    if not os.path.exists(dbfile):
        raise FileNotFoundError(f"Fichier de base de données introuvable : {dbfile}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{dbfile}_{timestamp}.bak"

    shutil.copy2(dbfile, backup_file)
    logger.info("Base de données sauvegardée dans : %s", backup_file)
    return backup_file
