"""Market data management module.

This module handles cryptocurrency market data including:
- Price updates from CoinMarketCap API
- Historical price storage and retrieval
- Currency rate management
"""

import logging
import sqlite3
import time

import pandas as pd
import pytz
import requests
import tzlocal
import streamlit as st

from modules.cmc import cmc

logger = logging.getLogger(__name__)


class Market:
    """Class for managing cryptocurrency market data and currency rates."""

    def __init__(self, db_path: str, cmc_token: str):
        """Initialize Market instance.

        Args:
            db_path: Path to SQLite database file
            cmc_token: CoinMarketCap API token
        """
        self.db_path = db_path
        self.cmc_token = cmc_token
        self.__init_database()
        self.local_timezone = tzlocal.get_localzone()

    def __init_database(self):
        """Initialize database tables and indexes if they don't exist."""
        logger.debug("Init database")
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS Market (timestamp INTEGER, token TEXT, price REAL)"
            )
            cur.execute(
                "CREATE TABLE IF NOT EXISTS Currency (timestamp INTEGER, currency TEXT, price REAL)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_currency ON Currency (timestamp, currency)"
            )
            con.commit()

    def getTokens(self) -> list:
        """Get list of all tokens in the database.

        Returns:
            List of token symbols
        """
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                "SELECT DISTINCT token from Market ORDER BY token", con
            )
            return df["token"].to_list()

    def getMarket(self) -> pd.DataFrame:
        """Get historical market data for all tokens.

        Returns:
            DataFrame with token prices over time or None if empty
        """
        logger.debug("Get market")
        with sqlite3.connect(self.db_path) as con:
            df_tokens = pd.read_sql_query("select DISTINCT token from Market", con)
            if df_tokens.empty:
                return None
            df_market = pd.DataFrame()
            for token in df_tokens["token"]:
                df = pd.read_sql_query(
                    f"SELECT timestamp, price AS '{token}' FROM Market WHERE token = '{token}'",
                    con,
                )
                if df.empty:
                    continue
                if df_market.empty:
                    df_market = df
                else:
                    df_market = df_market.merge(df, on="timestamp", how="outer")
            if df_market.empty:
                return None

            df_market["timestamp"] = pd.to_datetime(
                df_market["timestamp"], unit="s", utc=True
            ).dt.tz_convert(self.local_timezone)
            df_market.rename(columns={"timestamp": "Date"}, inplace=True)
            df_market.set_index("Date", inplace=True)
            df_market.sort_index(inplace=True)
            df_market = df_market.reindex(sorted(df_market.columns), axis=1)
            return df_market

    def get_token_market(
        self, token: str, from_timestamp: int = None, to_timestamp: int = None
    ) -> pd.DataFrame:
        """Get historical market data for a token.

        Args:
            token: Token symbol
            from_timestamp: Optional start timestamp
            to_timestamp: Optional end timestamp

        Returns:
            DataFrame with token prices over time or None if empty
        """
        logger.debug("Get token market")
        with sqlite3.connect(self.db_path) as con:
            if from_timestamp and to_timestamp:
                df = pd.read_sql_query(
                    f"SELECT timestamp AS Date, price AS Price from Market WHERE token = '{token}' AND timestamp >= {from_timestamp} AND timestamp <= {to_timestamp} ORDER BY timestamp;",
                    con,
                )
            elif from_timestamp:
                df = pd.read_sql_query(
                    f"SELECT timestamp AS Date, price AS Price from Market WHERE token = '{token}' AND timestamp >= {from_timestamp} ORDER BY timestamp;",
                    con,
                )
            elif to_timestamp:
                df = pd.read_sql_query(
                    f"SELECT timestamp AS Date, price AS Price from Market WHERE token = '{token}' AND timestamp <= {to_timestamp} ORDER BY timestamp;",
                    con,
                )
            else:
                df = pd.read_sql_query(
                    f"SELECT timestamp AS Date, price AS Price from Market WHERE token = '{token}' ORDER BY timestamp;",
                    con,
                )
            if df.empty:
                return None
            df["Date"] = pd.to_datetime(df["Date"], unit="s", utc=True)
            df["Date"] = df["Date"].dt.tz_convert(self.local_timezone)
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)
            return df

    def getLastMarket(self) -> pd.DataFrame:
        """Get most recent market data for all tokens.

        Returns:
            DataFrame with latest token prices or None if empty
        """
        logger.debug("Get last market")
        tokens_list = self.getTokens()
        if not tokens_list:
            logger.warning("No tokens available")
            return None
        with sqlite3.connect(self.db_path) as con:
            market_data = []
            for token in tokens_list:
                df = pd.read_sql_query(
                    f"SELECT timestamp, price AS '{token}' FROM Market WHERE token = '{token}' ORDER BY timestamp DESC LIMIT 1;",
                    con,
                )
                if df.empty:
                    continue
                market_data.append(
                    {
                        "token": token,
                        "timestamp": df["timestamp"][0],
                        "value": df[token][0],
                    }
                )
            market_df = pd.DataFrame(market_data)
            market_df.set_index("token", inplace=True)
            logger.debug("Last Market get size: %d", len(market_df))
            logger.debug("Last Market get:\n%s", market_df)
            return market_df

    def update_market(self, tokens: list = None, debug: bool = False):
        """Update market data with current prices and add new tokens.

        Args:
            tokens: Optional list of token symbols to add/update
        """
        logger.debug("Add tokens")

        known_tokens = self.getTokens()
        tokens = list(set(tokens + known_tokens))
        logger.debug("tokens: %s", str(tokens))

        timestamp = int(pd.Timestamp.now(tz=pytz.UTC).timestamp())
        cmc_prices = cmc(self.cmc_token)
        tokens_prices = cmc_prices.get_crypto_prices(tokens, debug=debug)
        if not tokens_prices:
            logger.info("No data available")
            raise ValueError("No data available")

        logger.debug("Adding %d tokens to database", len(tokens_prices))

        with sqlite3.connect(self.db_path) as con:
            for token in tokens_prices:
                cur = con.cursor()
                cur.execute(
                    "INSERT INTO Market (timestamp, token, price) VALUES (?, ?, ?)",
                    (timestamp, token, tokens_prices[token]["price"]),
                )
            con.commit()

    def get_last_timestamp(self) -> int:
        """Get timestamp of most recent market data.

        Returns:
            Unix timestamp of latest market data
        """
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                "SELECT MAX(timestamp) as timestamp from Market;", con
            )
            return df["timestamp"][0]

    def get_price(self, token: str, timestamp: int = None) -> float:
        """Get price of a token at given timestamp.

        Args:
            token: Token symbol
            timestamp: Optional timestamp, latest if None

        Returns:
            Token price or 0.0 if not found
        """
        with sqlite3.connect(self.db_path) as con:
            if timestamp:
                df = pd.read_sql_query(
                    f"SELECT price from Market WHERE token = '{token}' AND timestamp <= {timestamp} ORDER BY timestamp DESC LIMIT 1;",
                    con,
                )
            else:
                df = pd.read_sql_query(
                    f"SELECT price from Market WHERE token = '{token}' ORDER BY timestamp DESC LIMIT 1;",
                    con,
                )
        logger.debug("Get price: %s", df)
        if df.empty:
            return 0.0
        return df["price"][0]

    def get_prices(self, token: str) -> pd.DataFrame:
        """Get historical prices of a token.

        Args:
            token: Token symbol

        Returns:
            DataFrame with token prices over time
        """
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                f"SELECT timestamp, price from Market WHERE token = '{token}' ORDER BY timestamp;",
                con,
            )
            return df

    def drop_duplicate(self, table: str):
        """Drop duplicate rows from a table.

        Args:
            table: Table name
        """
        logger.debug("Drop duplicate from %s", table)
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(f"SELECT * from {table};", con)
            dupcount = df.duplicated().sum()
            logger.debug("Found %d rows with %f duplicated rows", len(df), dupcount)
            if dupcount > 0:
                logger.debug("Found %d duplicated rows. Dropping...", dupcount)
                df.drop_duplicates(inplace=True)
                df.to_sql(table, con, if_exists="replace", index=False)

    def __find_missing_timestamps(self) -> pd.DataFrame:
        """Find missing timestamps in the Currency table.

        Returns:
            DataFrame with missing timestamps
        """
        with sqlite3.connect(self.db_path) as con:
            df_timestamps = pd.read_sql_query(
                "SELECT DISTINCT timestamp from Market",
                con,
            )
            df_timestamps["timestamp"] = df_timestamps["timestamp"].apply(
                lambda x: int(
                    pd.Timestamp(
                        pd.to_datetime(x, unit="s", utc=True).strftime("%Y-%m-%d")
                        + " 14:30:00+00:00"
                    ).timestamp()
                )
            )
            df_timestamps.drop_duplicates(inplace=True)

            # remove timestamp greater than now_timestamp from df_timestamps
            now_timestamp = int(pd.Timestamp.now(tz=pytz.UTC).timestamp())
            logger.debug("Now timestamp: %d", now_timestamp)
            logger.debug(
                "to remove: %d",
                len(df_timestamps[df_timestamps["timestamp"] > now_timestamp]),
            )
            df_timestamps = df_timestamps[df_timestamps["timestamp"] <= now_timestamp]

            df_rate_timestamps = pd.read_sql_query(
                "SELECT DISTINCT timestamp from Currency",
                con,
            )
            # cree un dataframe avec les timestamp qui sont dans df_timestamps mais pas dans df_rate_timestamps
            df_ret = df_timestamps[
                ~df_timestamps["timestamp"].isin(df_rate_timestamps["timestamp"])
            ]
            logging.debug("Missing timestamps: %d", len(df_ret))
            return df_ret

    def update_currencies(self, debug: bool = False):
        """Update currency rates and add missing timestamps."""
        logger.debug("Update currencies")

        df_timestamps = self.__find_missing_timestamps()
        count = len(df_timestamps)
        if count == 0:
            logger.debug("No missing timestamps")
        else:
            idx = 0
            for timestamp in df_timestamps["timestamp"]:
                idx += 1
                # convert timestamp to datetime(YYYY-MM-DD)
                date = pd.to_datetime(timestamp, unit="s", utc=True).strftime(
                    "%Y-%m-%d"
                )
                rate_date = f"{date} 14:30:00+00:00"
                rate_timestamp = int(pd.Timestamp(rate_date).timestamp())
                logger.debug(
                    "%d/%d Timestamp: %d -> Date: %s -> Rate Date: %s -> Rate Timestamp: %d",
                    idx,
                    count,
                    timestamp,
                    date,
                    rate_date,
                    rate_timestamp,
                )

                # request the currency rate
                url = f"https://free.ratesdb.com/v1/rates?from=EUR&to=USD&date={date}"
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    logging.error(
                        "Error updating currencies. Code: %d", response.status_code
                    )
                    time.sleep(1)
                    raise ValueError("Error updating currencies")
                resp = response.json()

                logger.debug(
                    "Rate Timestamp: %d  - Rate: %f",
                    rate_timestamp,
                    resp["data"]["rates"]["USD"],
                )
                self.add_currency(rate_timestamp, "USD", resp["data"]["rates"]["USD"])

                # sleep 1 second to avoid api request rate limit
                time.sleep(1)

        # add current rate to Currency from CMC
        cmc_prices = cmc(self.cmc_token)
        price = cmc_prices.get_current_fiat_prices(debug=debug)
        logger.debug("Adding current rate to Currency: %s", price)
        for currency in price:
            self.add_currency(
                price[currency]["timestamp"], currency, price[currency]["price"]
            )

        # drop duplicate
        self.drop_duplicate("Currency")

    def add_currency(self, timestamp: int, currency: str, price: float):
        """Add currency rate to the database.

        Args:
            timestamp: Unix timestamp of the rate
            currency: Currency symbol
            price: Currency rate
        """
        logger.debug("Add currency: %s - %f", currency, price)
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO Currency (timestamp, currency, price) VALUES (?, ?, ?)",
                (timestamp, currency, price),
            )
            con.commit()

    def get_token_lowhigh(self, token: str, timestamp: int) -> pd.DataFrame:
        """Get the low and high values for a token at a given timestamp.

        Args:
            token: Token symbol
            timestamp: Unix timestamp

        Returns:
            DataFrame with low and high values
        """
        with sqlite3.connect(self.db_path) as con:
            df_low = pd.read_sql_query(
                f"SELECT timestamp, price from Market WHERE token = '{token}' AND timestamp <= {timestamp} ORDER BY timestamp DESC LIMIT 1;",
                con,
            )
            df_high = pd.read_sql_query(
                f"SELECT timestamp, price from Market WHERE token = '{token}' AND timestamp >= {timestamp} ORDER BY timestamp ASC LIMIT 1;",
                con,
            )
            return df_low, df_high

    def get_currency_lowhigh(self, currency: str, timestamp: int) -> pd.DataFrame:
        """Get the low and high values for a fiat currency at a given timestamp.

        Args:
            currency: Currency symbol (e.g., 'USD', 'EUR')
            timestamp: Unix timestamp

        Returns:
            Tuple of (df_low, df_high) DataFrames with low and high values
        """
        with sqlite3.connect(self.db_path) as con:
            df_low = pd.read_sql_query(
                f"SELECT timestamp, price from Currency WHERE currency = '{currency}' AND timestamp <= {timestamp} ORDER BY timestamp DESC LIMIT 1;",
                con,
            )
            df_high = pd.read_sql_query(
                f"SELECT timestamp, price from Currency WHERE currency = '{currency}' AND timestamp >= {timestamp} ORDER BY timestamp ASC LIMIT 1;",
                con,
            )
            return df_low, df_high
