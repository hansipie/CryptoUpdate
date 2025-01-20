import sqlite3
import time
import pandas as pd
import logging
import tzlocal
import pytz
import requests
from modules.cmc import cmc

logger = logging.getLogger(__name__)


class Market:
    def __init__(self, db_path: str, cmc_token: str):
        self.db_path = db_path
        self.cmc_token = cmc_token
        self.__initDatabase()
        self.local_timezone = tzlocal.get_localzone()

    def __initDatabase(self):
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

    # get all the tokens in the Market
    def getTokens(self) -> list:
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                "SELECT DISTINCT token from Market ORDER BY token", con
            )
            return df["token"].to_list()

    # get all the market over the time
    def getMarket(self) -> pd.DataFrame:
        logger.debug("Get market")
        with sqlite3.connect(self.db_path) as con:
            df_tokens = pd.read_sql_query("select DISTINCT token from Market", con)
            if df_tokens.empty:
                return None
            df_market = pd.DataFrame()
            for token in df_tokens["token"]:
                df = pd.read_sql_query(
                    f"SELECT timestamp, price AS '{token}' FROM Market WHERE token = '{token}' ORDER BY timestamp;",
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
            # df_market = df_market.fillna(0) # c'est mal de remplir les NaN ici
            df_market["timestamp"] = pd.to_datetime(
                df_market["timestamp"], unit="s", utc=True
            )
            df_market["timestamp"] = df_market["timestamp"].dt.tz_convert(
                self.local_timezone
            )
            df_market.rename(columns={"timestamp": "Date"}, inplace=True)
            df_market.set_index("Date", inplace=True)
            df_market = df_market.reindex(sorted(df_market.columns), axis=1)
            return df_market

    # get the last market
    def getLastMarket(self) -> pd.DataFrame:
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
            logger.debug(f"Last Market get size: {len(market_df)}")
            logger.debug(f"Last Market get:\n{market_df}")
            return market_df

    # update the market with the current prices
    # + add new tokens to the database with the current price
    def updateMarket(self, tokens: list = []):
        logger.debug("Add tokens")

        known_tokens = self.getTokens()
        tokens = list(set(tokens + known_tokens))
        logger.debug(f"tokens: {tokens}")

        timestamp = int(pd.Timestamp.now(tz=pytz.UTC).timestamp())
        cmc_prices = cmc(self.cmc_token)
        tokens_prices = cmc_prices.getCryptoPrices(tokens)
        if not tokens_prices:
            logger.warning("No data available")
            return

        logger.debug(f"Adding {len(tokens_prices)} tokens to database")

        with sqlite3.connect(self.db_path) as con:
            for token in tokens_prices:
                cur = con.cursor()
                cur.execute(
                    "INSERT INTO Market (timestamp, token, price) VALUES (?, ?, ?)",
                    (timestamp, token, tokens_prices[token]["price"]),
                )
            con.commit()

    # get the last timestamp
    def getLastTimestamp(self) -> int:
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                "SELECT MAX(timestamp) as timestamp from Market;", con
            )
            return df["timestamp"][0]

    # get the last price of a token
    def getLastPrice(self, token: str) -> float:
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                f"SELECT price from Market WHERE token = '{token}' ORDER BY timestamp DESC LIMIT 1;",
                con,
            )
            try:
                return df["price"][0]
            except IndexError:
                return 0.0

    # get the prices of a token
    def getPrices(self, token: str) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                f"SELECT timestamp, price from Market WHERE token = '{token}' ORDER BY timestamp;",
                con,
            )
            return df

    # drop the duplicate rows
    def dropDuplicate(self, table: str):
        logger.debug(f"Drop duplicate from {table}")
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(f"SELECT * from {table};", con)
            dupcount = df.duplicated().sum()
            logger.debug(f"Found {len(df)} rows with {dupcount} duplicated rows")
            if dupcount > 0:
                logger.debug(f"Found {dupcount} duplicated rows. Dropping...")
                df.drop_duplicates(inplace=True)
                df.to_sql(table, con, if_exists="replace", index=False)

    def __findMissingTimestamps(self) -> pd.DataFrame:
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
            logger.debug(f"Now timestamp: {now_timestamp}")
            logger.debug(
                f"to remove: {len(df_timestamps[df_timestamps["timestamp"] > now_timestamp])}"
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
            logging.debug(f"Missing timestamps: {len(df_ret)}")
            return df_ret

    def updateCurrencies(self):
        logger.debug("Update currencies")

        df_timestamps = self.__findMissingTimestamps()
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
                    f"{idx}/{count} Timestamp: {timestamp} -> Date: {date} -> Rate Date: {rate_date} -> Rate Timestamp: {rate_timestamp}"
                )

                # request the currency rate
                url = f"https://free.ratesdb.com/v1/rates?from=EUR&to=USD&date={date}"
                response = requests.get(url)
                if response.status_code != 200:
                    logging.error(
                        f"Error updating currencies. Code: {response.status_code}"
                    )
                    time.sleep(1)
                    return None
                resp = response.json()

                logger.debug(
                    f"Rate Timestamp: {rate_timestamp}  - Rate: {resp["data"]["rates"]["USD"]}"
                )
                self.addCurrency(rate_timestamp, "USD", resp["data"]["rates"]["USD"])

                # sleep 1 second to avoid api request rate limit
                time.sleep(1)

        # add current rate to Currency from CMC
        cmc_prices = cmc(self.cmc_token)
        price = cmc_prices.getCurrentFiatPrices()
        logger.debug(f"Adding current rate to Currency: {price}")
        for currency in price:
            self.addCurrency(
                price[currency]["timestamp"], currency, price[currency]["price"]
            )

        # drop duplicate
        self.dropDuplicate("Currency")

    def addCurrency(self, timestamp: int, currency: str, price: float):
        logger.debug(f"Add currency: {currency} - {price}")
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO Currency (timestamp, currency, price) VALUES (?, ?, ?)",
                (timestamp, currency, price),
            )
            con.commit()

    def getCurrency(self) -> pd.DataFrame:
        logger.debug("Get currency")
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query("SELECT * from Currency ORDER BY timestamp", con)
            if df.empty:
                return None
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
            df["timestamp"] = df["timestamp"].dt.tz_convert(self.local_timezone)
            df.rename(columns={"timestamp": "Date"}, inplace=True)
            df.set_index("Date", inplace=True)
            return df
