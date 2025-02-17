import os
import sqlite3
import time
import logging
import pandas as pd
import requests
import streamlit as st

from modules.database.market import Market
from modules.tools import interpolate_eurusd

logger = logging.getLogger(__name__)

st.title("Tests")

convert_tab, raccoon_tab = st.tabs(["Market to USD", "Connect to MarketRaccoon"])

with convert_tab:
    # List db files from data folder
    db_files = [
        f
        for f in os.listdir(st.session_state.settings["data_path"])
        if f.endswith(".bak") or f.endswith(".sqlite3")
    ]
    db_file = st.selectbox(
        "Select a database file", db_files, index=None, placeholder="Select a file"
    )
    logger.debug("Selected database file: %s", db_file)
    if db_file:
        db_filepath = os.path.join(st.session_state.settings["data_path"], db_file)
        with sqlite3.connect(db_filepath) as conn:
            cursor = conn.cursor()
            # get db description
            cursor.execute(
                """
                SELECT * FROM Market
                """
            )
            market = cursor.fetchall()
            cursor.execute(
                """
                SELECT * FROM Currency
                """
            )
            currency = cursor.fetchall()

        df_market = pd.DataFrame(market, columns=["timestamp", "symbol", "EUR"])
        df_currency = pd.DataFrame(currency, columns=["timestamp", "symbol", "price"])

        col, col2 = st.columns(2)
        with col:
            st.write(df_market)
        with col2:
            st.write(df_currency)

        if st.button("Convert to USD"):
            start_time = time.time()
            with st.spinner("Converting to USD..."):
                df_market["current_price"] = df_market.apply(
                    lambda x: x["EUR"]
                    * interpolate_eurusd(x["timestamp"], df_currency),
                    axis=1,
                )
            with st.spinner("Converting timestamp..."):
                df_market["last_updated"] = pd.to_datetime(
                    df_market["timestamp"], unit="s", utc=True
                )
            with st.spinner("Symbol to lowercase..."):
                df_market["symbol"] = df_market["symbol"].str.lower()

            # remove EUR and timestamp columns
            df_market.drop(columns=["EUR", "timestamp"], inplace=True)

            execution_time = time.time() - start_time
            logger.debug(
                "Execution time for USD conversion: %f seconds", execution_time
            )

            st.write(df_market)
            # write dataframe to db

            with sqlite3.connect(db_filepath + "_usd.sqlite3") as conn:
                df_market.to_sql("Market_USD", conn, if_exists="replace", index=False)

            logger.debug("Dataframe written to Market_USD table.")

with raccoon_tab:

    markgetdb = Market(
        st.session_state.settings["dbfile"],
        st.session_state.settings["coinmarketcap_token"],
    )

    available_tokens = markgetdb.getTokens()
    
    symbol = st.selectbox("Select a token", available_tokens)
    try:
        response = requests.get(
            f"{st.session_state.settings['marketraccoon_url']}/api/v1/quotes/all/{symbol}",
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            df_data = pd.DataFrame.from_dict(data, orient="columns")
            st.write(df_data)
        else:
            st.error(f"HTTP Error {response.status_code}.")
    except requests.ConnectionError:
        st.error("Connection to MarketRaccoon failed.")
        logger.error("Connection error during API healthcheck.")
    except requests.Timeout:
        st.error("API request timed out.")
        logger.error("API request timed out.")




