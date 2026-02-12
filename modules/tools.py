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

import numpy as np
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


def get_currency_symbol(currency_code: str = None) -> str:
    """Obtient le symbole pour un code devise donné.

    Args:
        currency_code: Code ISO devise (ex: "EUR", "USD").
                      Si None, utilise fiat_currency depuis settings.

    Returns:
        Symbole de devise (ex: "€", "$") ou le code lui-même si inconnu.
    """
    if currency_code is None:
        currency_code = st.session_state.settings.get("fiat_currency", "EUR")

    currency_symbols = {"EUR": "€", "USD": "$"}
    return currency_symbols.get(currency_code, currency_code)


def convert_price_to_target_currency(
    value: float, source_currency: str, target_currency: str = None
) -> float:
    """Convertit un montant d'une devise source vers une devise cible (taux actuel).

    Utilise le taux de change le plus récent. Pour une conversion avec taux
    historiques sur un DataFrame, utiliser convert_dataframe_prices_historical().

    Args:
        value: Montant à convertir
        source_currency: Devise source (ex: "USD", "EUR")
        target_currency: Devise cible (ex: "EUR", "GBP").
                        Si None, utilise fiat_currency depuis settings.

    Returns:
        Montant converti dans la devise cible
    """
    if target_currency is None:
        target_currency = st.session_state.settings.get("fiat_currency", "EUR")

    # Si devises identiques, pas de conversion
    if source_currency == target_currency:
        return value

    # Seul EUR↔USD supporté dans v1
    if source_currency not in ["EUR", "USD"] or target_currency not in ["EUR", "USD"]:
        logger.warning(
            "Conversion %s→%s non supportée (seul EUR↔USD disponible)",
            source_currency,
            target_currency,
        )
        return value

    # Récupérer le taux USD→EUR depuis MarketRaccoon API
    try:
        api_market = get_cached_api_market()
        df_rate = api_market.get_fiat_latest_rate_cached()

        if df_rate is None or df_rate.empty:
            logger.warning("Taux de change non disponible, retour valeur originale")
            return value

        usd_to_eur_rate = df_rate["price"].iloc[-1]  # Ex: 0.85 (1 USD = 0.85 EUR)

        # Conversion USD → EUR
        if source_currency == "USD" and target_currency == "EUR":
            return value * usd_to_eur_rate

        # Conversion EUR → USD
        elif source_currency == "EUR" and target_currency == "USD":
            return value / usd_to_eur_rate

        else:
            logger.warning(
                "Conversion %s→%s non supportée", source_currency, target_currency
            )
            return value

    except Exception as e:
        logger.error("Erreur conversion devise: %s", e)
        return value


def convert_dataframe_prices_historical(
    df: pd.DataFrame,
    price_column: str,
    source_currency: str,
    target_currency: str = None,
    fiat_rates_df: pd.DataFrame = None,
) -> pd.DataFrame:
    """Convertit les prix d'un DataFrame en utilisant les taux de change historiques.

    Utilise pd.merge_asof pour associer à chaque date de prix le taux de change
    le plus proche temporellement, garantissant une conversion précise même pour
    les données historiques.

    Args:
        df: DataFrame avec DatetimeIndex contenant les prix à convertir
        price_column: Nom de la colonne contenant les prix (ex: "Price")
        source_currency: Devise source (ex: "USD")
        target_currency: Devise cible. Si None, utilise fiat_currency depuis settings.
        fiat_rates_df: DataFrame avec DatetimeIndex et colonne "price" contenant
                      les taux USD→EUR historiques. Si None, fallback sur taux actuel.

    Returns:
        Copie du DataFrame avec les prix convertis
    """
    if target_currency is None:
        target_currency = st.session_state.settings.get("fiat_currency", "EUR")

    if source_currency == target_currency:
        return df

    # Seul EUR↔USD supporté
    if source_currency not in ["EUR", "USD"] or target_currency not in ["EUR", "USD"]:
        logger.warning(
            "Conversion historique %s→%s non supportée (seul EUR↔USD disponible)",
            source_currency,
            target_currency,
        )
        return df

    # Fallback sur taux actuel si pas de données historiques
    if fiat_rates_df is None or fiat_rates_df.empty:
        logger.warning(
            "Pas de taux historiques disponibles, utilisation du taux actuel"
        )
        df = df.copy()
        df[price_column] = df[price_column].apply(
            lambda x: convert_price_to_target_currency(
                x, source_currency, target_currency
            )
        )
        return df

    df = df.copy()

    # Préparer les prix et taux pour merge_asof (nécessite des colonnes, pas un index)
    prices = df[[price_column]].reset_index()
    prices.columns = ["Date", "price_value"]

    rates = fiat_rates_df[["price"]].sort_index().reset_index()
    rates.columns = ["Date", "rate"]

    # merge_asof : associer chaque date de prix au taux le plus proche
    merged = pd.merge_asof(
        prices.sort_values("Date"),
        rates.sort_values("Date"),
        on="Date",
        direction="nearest",
    )

    logger.info(
        "Conversion historique %s→%s : %d prix, taux min=%.4f max=%.4f",
        source_currency,
        target_currency,
        len(merged),
        merged["rate"].min(),
        merged["rate"].max(),
    )

    # Appliquer la conversion selon la direction
    if source_currency == "USD" and target_currency == "EUR":
        converted = merged["price_value"] * merged["rate"]
    else:  # EUR → USD
        converted = merged["price_value"] / merged["rate"]

    # Remettre les valeurs converties dans le DataFrame original (même ordre d'index)
    df[price_column] = converted.values

    return df


def get_cached_api_market() -> ApiMarket:
    """Get or create cached ApiMarket instance in session state.

    This singleton pattern prevents creating multiple ApiMarket instances
    per session and enables caching of API responses.

    Returns:
        ApiMarket instance with caching enabled
    """
    if "api_market_instance" not in st.session_state:
        settings = st.session_state.settings
        cache_file = os.path.join(settings["data_path"], "api_cache.json")

        st.session_state.api_market_instance = ApiMarket(
            settings["marketraccoon_url"],
            api_key=settings.get("marketraccoon_token"),
            cache_file=cache_file,
        )
        logger.debug(
            "Created cached ApiMarket instance with cache file: %s", cache_file
        )

    return st.session_state.api_market_instance


# Conversion d'une valeur fiat vers la devise cible définie dans les settings
def convert_fiat_to_settings_currency(
    value: float, input_currency: str = "EUR"
) -> float:
    """
    Convertit une valeur fiat (ex: EUR, USD) vers la devise cible définie dans les settings.

    LIMITATION ACTUELLE: Seules les conversions EUR<->USD sont supportées.
    Pour les autres devises, la valeur originale est retournée sans conversion.

    Args:
        value: Montant à convertir
        input_currency: Devise d'entrée (ex: "EUR", "USD")

    Returns:
        Montant converti dans la devise cible (ou valeur originale si conversion non supportée)
    """
    settings = st.session_state.settings
    target_currency = settings.get("fiat_currency", "EUR")

    # Si les devises sont identiques, pas de conversion nécessaire
    if input_currency == target_currency:
        return value

    # Si ni EUR ni USD n'est impliqué, pas de conversion possible pour le moment
    if input_currency not in ["EUR", "USD"] or target_currency not in ["EUR", "USD"]:
        logger.warning(
            "Conversion %s -> %s non supportée. Seules les conversions EUR<->USD sont disponibles.",
            input_currency,
            target_currency,
        )
        return value

    # Utiliser ApiMarket pour obtenir les taux de change EUR/USD avec cache
    api_market = get_cached_api_market()

    try:
        # Récupérer les derniers taux de change (avec cache)
        rates_df = api_market.get_fiat_latest_rate_cached()

        if rates_df is None or rates_df.empty:
            logger.warning(
                "Aucun taux de change disponible, retour de la valeur originale"
            )
            return value

        # Prendre le taux le plus récent
        # L'API MarketRaccoon retourne le champ "eur" qui représente le taux USD->EUR
        # Exemple: si eur=0.8563, cela signifie 1 USD = 0.8563 EUR
        latest_rate = rates_df.iloc[-1]["price"]

        # Conversion selon les devises
        if input_currency == "EUR" and target_currency == "USD":
            # EUR vers USD: diviser par le taux USD->EUR
            # Exemple: 100 EUR / 0.8563 = 116.78 USD
            converted_value = value / latest_rate
        elif input_currency == "USD" and target_currency == "EUR":
            # USD vers EUR: multiplier par le taux USD->EUR
            # Exemple: 100 USD * 0.8563 = 85.63 EUR
            converted_value = value * latest_rate
        else:
            # Ne devrait pas arriver vu la vérification ci-dessus
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
        logger.error(
            "Erreur conversion %s -> %s: %s", input_currency, target_currency, e
        )
        return None


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
    custom.set(
        "last_update", str(int(pd.Timestamp.now(tz="UTC").timestamp())), "integer"
    )


def parse_last_update(last_update_data: tuple) -> pd.Timestamp:
    """Parse last_update from Customdata based on its stored type.

    Args:
        last_update_data: Tuple (value, type) from Customdata.get()

    Returns:
        pd.Timestamp with timezone UTC
    """
    value, value_type = last_update_data

    if value_type == "integer":
        timestamp = int(value)
    elif value_type == "float":
        timestamp = int(float(value))
    else:
        # Fallback: try float first, then int
        try:
            timestamp = int(float(value))
        except ValueError:
            timestamp = int(value)

    return pd.Timestamp.fromtimestamp(timestamp, tz="UTC")


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

    # Get target currency from settings
    target_currency = st.session_state.settings.get("fiat_currency", "EUR")

    market = Market(
        st.session_state.settings["dbfile"],
        st.session_state.settings["coinmarketcap_token"],
    )

    def calculate_value(row):
        token = row.name
        amount = row["amount"]

        if is_fiat(token):
            # For fiat currencies, the amount is in the token's native currency
            # Example: if token is "USD", amount is in USD
            # Convert from token currency to target currency
            return convert_fiat_to_settings_currency(amount, input_currency=token)
        else:
            # For crypto, get price in EUR and convert to target currency
            price_eur = market.get_price(token)
            value_in_eur = amount * price_eur
            return convert_fiat_to_settings_currency(value_in_eur, input_currency="EUR")

    # Create column with dynamic currency symbol
    df[f"value({target_currency})"] = df.apply(calculate_value, axis=1)

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
    st.session_state.settings["marketraccoon_token"] = settings["MarketRaccoon"].get(
        "token", ""
    )
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

    # Ensure data and archive directories exist and are writable. If creation
    # fails, fall back to a safe local path inside the project directory.
    try:
        os.makedirs(st.session_state.settings["data_path"], exist_ok=True)
    except Exception as e:
        logger.error(
            "Unable to create data_path %s: %s",
            st.session_state.settings["data_path"],
            e,
        )
        fallback_data = os.path.join(os.getcwd(), "data")
        try:
            os.makedirs(fallback_data, exist_ok=True)
            st.session_state.settings["data_path"] = fallback_data
            logger.info("Falling back to data_path: %s", fallback_data)
        except Exception as e2:
            logger.critical(
                "Unable to create fallback data path %s: %s", fallback_data, e2
            )

    try:
        os.makedirs(st.session_state.settings["archive_path"], exist_ok=True)
    except Exception as e:
        logger.warning(
            "Unable to create archive_path %s: %s",
            st.session_state.settings["archive_path"],
            e,
        )

    # Ensure the directory for the DB file exists and that the DB file is
    # creatable. If not, try a fallback local DB file.
    db_dir = os.path.dirname(st.session_state.settings["dbfile"])
    if db_dir:
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            logger.error("Unable to create db directory %s: %s", db_dir, e)

    try:
        import sqlite3 as _sqlite

        # Attempt to open/create the database file
        with _sqlite.connect(st.session_state.settings["dbfile"]) as _conn:
            pass
    except Exception as e:
        logger.error(
            "Unable to create/open DB file %s: %s",
            st.session_state.settings["dbfile"],
            e,
        )
        fallback_db = os.path.join(os.getcwd(), "db.sqlite3")
        try:
            with _sqlite.connect(fallback_db) as _conn:
                pass
            st.session_state.settings["dbfile"] = fallback_db
            logger.info("Falling back to dbfile: %s", fallback_db)
        except Exception as e2:
            logger.critical("Unable to create fallback DB file %s: %s", fallback_db, e2)

    # Load fiat currency setting
    st.session_state.settings["fiat_currency"] = settings.get("FiatCurrency", {}).get(
        "currency", "EUR"
    )

    # Load UI preferences
    st.session_state.settings["show_empty_portfolios"] = settings.get(
        "UIPreferences", {}
    ).get("show_empty_portfolios", True)
    st.session_state.settings["graphs_selected_tokens"] = settings.get(
        "UIPreferences", {}
    ).get("graphs_selected_tokens", [])


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
    """Interpolate the token value at a given timestamp from the database

    Args:
        token: Token symbol (crypto or fiat currency)
        timestamp: Unix timestamp
        dbfile: Path to database file

    Returns:
        Price in EUR (for crypto) or exchange rate (for fiat)
        EUR returns 1.0 as it's the base currency
    """
    logger.debug(
        "Interpolate token - Token: %s - Timestamp: %d - from the database",
        token,
        timestamp,
    )
    market = Market(dbfile, st.session_state.settings["coinmarketcap_token"])

    # Special case: EUR is the base currency, so its "price" is always 1.0
    if token == "EUR":
        logger.debug("Token is EUR (base currency), returning 1.0")
        return 1.0

    # Check if token is a fiat currency
    if is_fiat(token):
        logger.debug("Token %s is a fiat currency, querying Currency table", token)
        df_low, df_high = market.get_currency_lowhigh(token, timestamp)
    else:
        logger.debug("Token %s is a cryptocurrency, querying Market table", token)
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


def batch_convert_historical(
    df: pd.DataFrame,
    amount_column: str,
    source_token_column: str,
    target_token: str,
    timestamp_column: str,
    dbfile: str,
) -> pd.Series:
    """Convert amounts in a DataFrame using historical rates via calculate_crypto_rate().

    Groups unique (source_token, timestamp) pairs to minimize DB queries,
    then maps the rates back to produce converted amounts.

    Args:
        df: DataFrame containing the data
        amount_column: Column name with amounts to convert
        source_token_column: Column name containing the source token per row
        target_token: Target token/currency to convert to
        timestamp_column: Column name containing unix timestamps
        dbfile: Path to database file

    Returns:
        Series with converted amounts (same index as df)
    """
    if df.empty:
        return pd.Series(dtype=float)

    # Build unique pairs to query
    pairs = df[[source_token_column, timestamp_column]].drop_duplicates()
    rate_cache = {}
    for _, row in pairs.iterrows():
        src = row[source_token_column]
        ts = int(row[timestamp_column])
        if src == target_token:
            rate_cache[(src, ts)] = 1.0
        else:
            rate = calculate_crypto_rate(src, target_token, ts, dbfile)
            rate_cache[(src, ts)] = rate

    # Map rates back and compute converted amounts
    rates = df.apply(
        lambda row: rate_cache.get(
            (row[source_token_column], int(row[timestamp_column]))
        ),
        axis=1,
    )
    amounts = pd.to_numeric(df[amount_column], errors="coerce")
    converted = amounts * rates
    return converted


def _get_api_latest_prices() -> dict:
    """Fetch latest USD prices for all tokens from MarketRaccoon API.

    Returns:
        Dict mapping symbol to USD price, e.g. {"BTC": 97000.0, "ETH": 3200.0}
    """
    api = get_cached_api_market()

    # Get list of tokens we actually use from the database
    try:
        portfolios = Portfolios(st.session_state.settings["dbfile"])
        portfolio_names = portfolios.get_portfolio_names()
        portfolio_tokens = []
        for pname in portfolio_names:
            portfolio_tokens.extend(portfolios.get_tokens(pname).keys())
        portfolio_tokens = list(set(portfolio_tokens))
        logger.debug("Portfolio tokens: %s", portfolio_tokens)

        # Fetch prices with symbol filter to avoid duplicates
        # NOTE: Bypass cache to pass symbols parameter
        latest_df = api.get_cryptocurrency_latest(symbols=portfolio_tokens)
    except Exception as e:
        logger.warning("Could not get portfolio tokens, fetching all: %s", e)
        latest_df = api.get_cryptocurrency_latest()

    if latest_df is None or latest_df.empty:
        logger.warning("No latest cryptocurrency data from API")
        return {}

    coins_df = api.get_coins_cached()
    if coins_df is None or coins_df.empty:
        logger.warning("No coins data from API")
        return {}

    # Build id -> symbol mapping
    id_to_symbol = dict(zip(coins_df["id"], coins_df["symbol"]))

    logger.debug("Latest df columns: %s", latest_df.columns.tolist())
    logger.debug("Latest df shape: %s", latest_df.shape)

    # Sort by rank (ascending) so the highest-ranked coin wins for duplicate symbols
    # e.g. Bitcoin (rank=1) beats "Bitcoin AI" (rank=9000+) for symbol "BTC"
    if "rank" in latest_df.columns:
        latest_df = latest_df.sort_values("rank", ascending=True, na_position="last")

    # latest_df has columns: coin (id), price, rank, ...
    prices = {}
    for _, row in latest_df.iterrows():
        coin_id = row["coin"]
        symbol = id_to_symbol.get(coin_id)
        if symbol:
            # If symbol already exists, keep the one with better rank (lower is better)
            if symbol in prices:
                logger.debug(
                    "Duplicate symbol %s found (coin_id=%d): keeping higher-ranked coin",
                    symbol,
                    coin_id,
                )
                continue
            prices[symbol] = float(row["price"])
            logger.info(
                "API price: %s (coin_id=%d) = %.8f USD", symbol, coin_id, row["price"]
            )
        else:
            logger.debug("No symbol found for coin_id=%s", coin_id)

    logger.info("API: fetched %d token prices", len(prices))
    return prices


def _get_api_fiat_rate() -> float:
    """Fetch the latest USD→EUR rate from MarketRaccoon API (cached).

    Returns:
        USD to EUR rate (e.g. 0.85 means 1 USD = 0.85 EUR), or None on error
    """
    api = get_cached_api_market()
    fiat_df = api.get_fiat_latest_rate()
    if fiat_df is not None and not fiat_df.empty:
        rate = fiat_df.iloc[-1]["price"]
        logger.info("API fiat rate USD→EUR: %s", rate)
        return rate
    logger.error(
        "API fiat rate unavailable - fiat_df is %s",
        "None" if fiat_df is None else "empty",
    )
    return None


def _interpolate_from_series(series: pd.Series, timestamp: int) -> float:
    """Interpolate a value from a pandas Series (DatetimeIndex -> float) at a Unix timestamp.

    Args:
        series: Series with DatetimeIndex and float values (prices in USD)
        timestamp: Unix timestamp to interpolate at

    Returns:
        Interpolated float value, or None if series is empty
    """
    if series is None or series.empty:
        return None

    # Convert DatetimeIndex to Unix timestamps
    ts_array = series.index.astype(np.int64) // 10**9
    return float(np.interp(timestamp, ts_array, series.values))


def calculate_crypto_rate_api(
    token_a: str,
    token_b: str,
    prices_usd: dict = None,
    usd_to_eur: float = None,
) -> float:
    """Calculate the current rate between two tokens using MarketRaccoon API.

    All crypto prices are in USD. Fiat rates use get_fiat_latest_rate_cached().

    Args:
        token_a: Numerator token (e.g. "BTC")
        token_b: Denominator token (e.g. "EUR")
        prices_usd: Pre-loaded dict of symbol→USD price. If None, fetched internally.
        usd_to_eur: Pre-loaded USD→EUR rate. If None, fetched internally.

    Returns:
        Rate: how many token_b per 1 token_a, or None on error
    """
    if prices_usd is None:
        prices_usd = _get_api_latest_prices()
    if usd_to_eur is None:
        usd_to_eur = _get_api_fiat_rate()

    def price_usd(token):
        if token == "USD":
            return 1.0
        if token == "EUR":
            # 1 EUR = 1/usd_to_eur USD  (e.g. 1/0.85 = 1.176)
            return (1.0 / usd_to_eur) if usd_to_eur else None
        return prices_usd.get(token)

    pa = price_usd(token_a)
    pb = price_usd(token_b)
    if pa is None or pb is None or pb == 0:
        logger.warning(
            "Cannot compute API rate %s/%s: pa=%s pb=%s", token_a, token_b, pa, pb
        )
        return None
    rate = pa / pb
    logger.debug("API rate: 1 %s = %f %s", token_a, rate, token_b)
    return rate


def batch_convert_historical_api(
    df: pd.DataFrame,
    amount_column: str,
    source_token_column: str,
    target_token: str,
    timestamp_column: str,
) -> pd.Series:
    """Convert amounts using historical API data (MarketRaccoon).

    Pre-loads historical price series per token, then interpolates locally.

    Args:
        df: DataFrame containing the data
        amount_column: Column with amounts to convert
        source_token_column: Column with source token per row
        target_token: Target token/currency
        timestamp_column: Column with unix timestamps

    Returns:
        Series with converted amounts (same index as df)
    """
    if df.empty:
        return pd.Series(dtype=float)

    api = get_cached_api_market()

    # Collect all unique tokens (sources + target)
    all_tokens = set(df[source_token_column].unique())
    all_tokens.add(target_token)

    min_ts = int(df[timestamp_column].min())
    max_ts = int(df[timestamp_column].max())

    # Pre-load price series for each token (in USD)
    series_cache = {}
    for token in all_tokens:
        if token == "USD":
            series_cache[token] = None  # Always 1.0
        elif token == "EUR":
            # Fetch fiat history -> Series of USD->EUR rates
            fiat_df = api.get_currency()
            if fiat_df is not None and not fiat_df.empty:
                # price = usd_to_eur rate, we need price in USD: 1/rate
                series_cache[token] = 1.0 / fiat_df["price"]
            else:
                series_cache[token] = None
        else:
            crypto_df = api.get_cryptocurrency_market_cached(
                token_symbol=token, from_timestamp=min_ts, to_timestamp=max_ts
            )
            if crypto_df is not None and not crypto_df.empty:
                series_cache[token] = crypto_df["Price"]
            else:
                series_cache[token] = None

    def _price_usd(token, ts):
        if token == "USD":
            return 1.0
        s = series_cache.get(token)
        if s is None:
            return None
        return _interpolate_from_series(s, ts)

    # Build unique pairs to minimize interpolations
    pairs = df[[source_token_column, timestamp_column]].drop_duplicates()
    rate_cache = {}
    for _, row in pairs.iterrows():
        src = row[source_token_column]
        ts = int(row[timestamp_column])
        if src == target_token:
            rate_cache[(src, ts)] = 1.0
        else:
            p_src = _price_usd(src, ts)
            p_tgt = _price_usd(target_token, ts)
            if p_src is not None and p_tgt is not None and p_tgt != 0:
                rate_cache[(src, ts)] = p_src / p_tgt
            else:
                rate_cache[(src, ts)] = None

    # Map rates back
    rates = df.apply(
        lambda row: rate_cache.get(
            (row[source_token_column], int(row[timestamp_column]))
        ),
        axis=1,
    )
    amounts = pd.to_numeric(df[amount_column], errors="coerce")
    return amounts * rates


def calc_perf_api(
    df: pd.DataFrame,
    col_token: str,
    col_rate: str,
    col_currency: str = None,
    prices_usd: dict = None,
    usd_to_eur: float = None,
) -> pd.DataFrame:
    """Calculate current performance using MarketRaccoon API prices.

    Args:
        df: DataFrame with operations data
        col_token: Column containing token symbols
        col_rate: Column containing original rates
        col_currency: Column containing currency symbols. When provided, Current Rate
                     is calculated as the token price in that currency (matching Buy Rate units).
        prices_usd: Pre-loaded dict of symbol→USD price. If None, fetched internally.
        usd_to_eur: Pre-loaded USD→EUR rate. If None, fetched internally.

    Returns:
        DataFrame with Current Rate and Perf. columns added
    """
    if prices_usd is None:
        prices_usd = _get_api_latest_prices()
    if not prices_usd:
        df["Current Rate"] = None
        df["Perf."] = None
        return df

    if usd_to_eur is None:
        usd_to_eur = _get_api_fiat_rate()

    # If col_currency is provided, calculate Current Rate as token price in that currency
    # This matches the Buy Rate semantics: From/To where From is in col_currency
    if col_currency:
        logger.debug(
            "calc_perf_api with currency conversion - usd_to_eur=%s", usd_to_eur
        )

        def get_token_price_in_currency(token, currency):
            """Get token price expressed in the given currency."""
            # Get both prices in USD
            token_price_usd = prices_usd.get(token)
            if token_price_usd is None:
                logger.debug("No USD price for token %s", token)
                return None

            logger.debug(
                "Token %s: USD price = %f, converting to %s",
                token,
                token_price_usd,
                currency,
            )

            # Convert token USD price to target currency
            if currency == "USD":
                return token_price_usd
            elif currency == "EUR":
                if usd_to_eur is not None:
                    converted = token_price_usd * usd_to_eur
                    logger.debug(
                        "Converted %f USD * %f = %f EUR",
                        token_price_usd,
                        usd_to_eur,
                        converted,
                    )
                    return converted
                else:
                    logger.warning(
                        "USD→EUR rate unavailable for %s, returning USD price", token
                    )
                    return (
                        token_price_usd  # Return USD price as fallback instead of None
                    )
            else:
                logger.warning(
                    "Unsupported currency: %s, returning USD price", currency
                )
                return token_price_usd  # Return USD price as fallback

        df["Current Rate"] = df.apply(
            lambda row: get_token_price_in_currency(row[col_token], row[col_currency]),
            axis=1,
        )
    else:
        # Fallback to old behavior: direct token price in target currency
        target_currency = st.session_state.settings.get("fiat_currency", "EUR")

        def convert_to_target(price_usd_val, token):
            """Convert a USD price to the target fiat currency."""
            if price_usd_val is None:
                return None
            if target_currency == "USD":
                return price_usd_val
            if target_currency == "EUR":
                if usd_to_eur is not None:
                    return price_usd_val * usd_to_eur
                logger.warning("USD→EUR rate unavailable, cannot convert %s", token)
                return None
            return price_usd_val

        def get_price_target(token):
            usd_price = prices_usd.get(token)
            return convert_to_target(usd_price, token)

        df["Current Rate"] = df[col_token].map(get_price_target)

    df["Perf."] = ((df["Current Rate"] * 100) / df[col_rate]) - 100
    return df


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
