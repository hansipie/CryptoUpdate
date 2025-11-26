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

import pandas as pd
import requests
import streamlit as st

from modules.database.customdata import Customdata
from modules.database.market import Market
from modules.database.portfolios import Portfolios
from modules.database.tokensdb import TokensDatabase
from modules.database.apimarket import ApiMarket
from modules.utils import debug_prefix, interpolate

logger = logging.getLogger(__name__)


# Conversion d'une valeur fiat vers la devise cible définie dans les settings
def convert_fiat_to_settings_currency(
    value: float, input_currency: str = "EUR"
) -> float:
    """
    Convertit une valeur fiat (ex: EUR, USD) vers la devise cible définie dans les settings.

    Args:
        value: Montant à convertir
        input_currency: Devise d'entrée (ex: "EUR", "USD")

    Returns:
        Montant converti dans la devise cible
    """
    settings = st.session_state.settings
    target_currency = settings.get("fiat_currency", "EUR")

    # Si les devises sont identiques, pas de conversion nécessaire
    if input_currency == target_currency:
        return value

    # Utiliser ApiMarket pour obtenir les taux de change
    api_market = ApiMarket(settings["marketraccoon_url"])

    try:
        # Récupérer les derniers taux de change
        rates_df = api_market.get_fiat_latest_rate()

        if rates_df is None or rates_df.empty:
            logger.warning(
                "Aucun taux de change disponible, retour de la valeur originale"
            )
            return value

        # Prendre le taux le plus récent
        latest_rate = rates_df.iloc[-1]["price"]

        # Conversion selon les devises
        if input_currency == "EUR" and target_currency == "USD":
            # EUR vers USD
            converted_value = value * latest_rate
        elif input_currency == "USD" and target_currency == "EUR":
            # USD vers EUR
            converted_value = value / latest_rate
        else:
            # Autres conversions non supportées pour le moment
            logger.warning(
                "Conversion %s -> %s non supportée", input_currency, target_currency
            )
            return value

        logger.debug(
            "Conversion %s %s -> %s %s (taux: %s)",
            value,
            input_currency,
            converted_value,
            target_currency,
            latest_rate,
        )
        return converted_value

    except (requests.RequestException, KeyError, ValueError) as e:
        logger.error("Erreur conversion %s -> %s: %s", input_currency, target_currency, e)
        return value


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


def is_fiat(token: str) -> bool:
    """Check if the token is a fiat currency"""
    return token in ["USD", "EUR"]


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
        * (market.get_price(row.name) if not is_fiat(row.name) else 1.0),
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
    st.session_state.settings["ai_apitoken"] = settings["AI"]["token"]
    st.session_state.settings["debug_flag"] = settings["Debug"]["flag"] == "True"

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

    # Load fiat currency setting
    st.session_state.settings["fiat_currency"] = settings.get(
        "FiatCurrency", {}
    ).get("currency", "EUR")


def interpolate_price(
    df_low: pd.DataFrame, df_high: pd.DataFrame, timestamp: int, token: str = ""
) -> float:
    """Interpolate the price at a given timestamp from two dataframes"""
    if df_high.empty:
        logger.debug(
            "No high data found for token: %s at timestamp: %d ... using low",
            token,
            timestamp,
        )
        df_high = df_low.copy()

    if df_low.empty:
        logger.warning("No data found for token: %s at timestamp: %d", token, timestamp)
        return None

    logger.debug(
        "Interpolate price - Token: %s - Timestamp: %d\nLow:\n%s\nHigh:\n%s",
        token,
        timestamp,
        df_low,
        df_high,
    )

    # Interpoler la valeur
    try:
        price_low = df_low["price"].iloc[-1]
        price_high = df_high["price"].iloc[0]
        timestamp_low = df_low["timestamp"].iloc[-1]
        timestamp_high = df_high["timestamp"].iloc[0]
    except (IndexError, KeyError) as e:
        logger.error("Error interpolating price: %s", e)
        return None
    price = interpolate(timestamp_low, price_low, timestamp_high, price_high, timestamp)
    logger.debug("Price: %f", price)
    return price


def __interpolate_token(token: str, timestamp: int, dbfile: str) -> float:
    """Interpolate the token value at a given timestamp from the database"""
    logger.debug(
        "Interpolate token - Token: %s - Timestamp: %d - from the database",
        token,
        timestamp,
    )
    market = Market(dbfile, st.session_state.settings["coinmarketcap_token"])
    df_low, df_high = market.get_token_lowhigh(token, timestamp)

    return interpolate_price(df_low, df_high, timestamp, token)


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

    value_a = __interpolate_token(token_a, timestamp, dbfile)
    value_b = __interpolate_token(token_b, timestamp, dbfile)
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
