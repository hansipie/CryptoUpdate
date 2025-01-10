import sqlite3
import pandas as pd
import logging
import tzlocal
import pytz
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
            #df_market = df_market.fillna(0) # c'est mal de remplir les NaN ici
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
    def getLastMarket(self) -> dict:
        logger.debug("Get last market")
        tokens_list = self.getTokens()
        if not tokens_list:
            logger.warning("No tokens available")
            return None
        with sqlite3.connect(self.db_path) as con:
            market_dict = {}
            for token in tokens_list:
                df = pd.read_sql_query(
                    f"SELECT timestamp, price AS '{token}' FROM Market WHERE token = '{token}' ORDER BY timestamp DESC LIMIT 1;",
                    con,
                )
                if df.empty:
                    continue
                market_dict[token] = {"price": df[token][0], "timestamp": df["timestamp"][0]}
            logger.debug(f"Last Market get size: {len(market_dict)}")
            return market_dict

    # update the market with the current prices
    def updateMarket(self):
        logger.debug("Update market")
        tokens = self.getMarket()
        self.addTokens(tokens)

    # add tokens to the database with the current price
    def addTokens(self, tokens: list = []):
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
            return df["price"][0]

    # get the prices of a token
    def getPrices(self, token: str) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                f"SELECT timestamp, price from Market WHERE token = '{token}' ORDER BY timestamp;",
                con,
            )
            return df

    # drop the duplicate rows
    def dropDuplicate(self):
        logger.debug("Drop duplicate")
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query("SELECT * from Market;", con)
            dupcount = df.duplicated().sum()
            logger.debug(f"Found {len(df)} rows with {dupcount} duplicated rows")
            if dupcount > 0:
                logger.debug(f"Found {dupcount} duplicated rows. Dropping...")
                df.drop_duplicates(inplace=True)
                df.to_sql("Market", con, if_exists="replace", index=False)
