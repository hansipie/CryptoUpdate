import sqlite3
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class HistoryBase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initDatabase()
        self.df_balance = pd.DataFrame()
        self.df_tokencount = pd.DataFrame()
        self.df_market = pd.DataFrame()
        self.df_sum = pd.DataFrame()

    def initDatabase(self):
        logger.debug("Init database")
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS Database (timestamp INTEGER, token TEXT, price REAL, count REAL)"
        )
        con.commit()
        con.close()

    def getSums(self, con) -> pd.DataFrame:
        logger.debug("Get sums")
        df = pd.read_sql_query(
            "SELECT DISTINCT timestamp from Database ORDER BY timestamp", con
        )
        df_sum = pd.DataFrame(columns=["datetime", "value"])
        for mytime in df["timestamp"]:
            dftmp = pd.read_sql_query(
                f"SELECT ROUND(sum(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END)), 2) as value, DATETIME(timestamp, 'unixepoch') AS datetime from Database WHERE timestamp = {str(mytime)};",
                con,
            )
            df_sum.loc[len(df_sum)] = [dftmp["datetime"][0], dftmp["value"][0]]
        df_sum.set_index("datetime", inplace=True)
        return df_sum

    def getBalances(self, con) -> pd.DataFrame:
        logger.debug("Get balances")
        df_tokens = pd.read_sql_query("select DISTINCT token from Database", con)
        df_balance = pd.DataFrame()
        for token in df_tokens["token"]:
            df = pd.read_sql_query(
                f"SELECT DATETIME(timestamp, 'unixepoch') AS datetime, ROUND(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END), 2) AS '{token}' FROM Database WHERE token = '{token}' ORDER BY timestamp;",
                con,
            )
            df.set_index("datetime", inplace=True)
            if df_balance.empty:
                df_balance = df
            else:
                df_balance = df_balance.join(df, how="outer")
        df_balance = df_balance.fillna(0)
        df_balance.sort_index()
        return df_balance

    def getTokenCounts(self, con) -> pd.DataFrame:
        logger.debug("Get token counts")
        df_tokens = pd.read_sql_query("select DISTINCT token from Database", con)
        df_tokencount = pd.DataFrame()
        for token in df_tokens["token"]:
            df = pd.read_sql_query(
                f"SELECT DATETIME(timestamp, 'unixepoch') AS datetime, count AS '{token}' FROM Database WHERE token = '{token}' ORDER BY timestamp;",
                con,
            )
            df.set_index("datetime", inplace=True)
            if df_tokencount.empty:
                df_tokencount = df
            else:
                df_tokencount = df_tokencount.join(df, how="outer")
        df_tokencount = df_tokencount.fillna(0)
        df_tokencount.sort_index()
        return df_tokencount

    def getMarket(self, con) -> pd.DataFrame:
        logger.debug("Get market")
        df_tokens = pd.read_sql_query("select DISTINCT token from Database", con)
        df_market = pd.DataFrame()
        for token in df_tokens["token"]:
            df = pd.read_sql_query(
                f"SELECT DATETIME(timestamp, 'unixepoch') AS datetime, price AS '{token}' FROM Database WHERE token = '{token}' ORDER BY timestamp;",
                con,
            )
            df.set_index("datetime", inplace=True)
            if df_market.empty:
                df_market = df
            else:
                df_market = df_market.join(df, how="outer")
        df_market = df_market.fillna(0)
        df_market.sort_index()
        return df_market

    def makeDataframes(self):
        logger.debug("Make dataframes")
        con = sqlite3.connect(self.db_path)
        self.df_sum = self.getSums(con)
        self.df_balance = self.getBalances(con)
        self.df_tokencount = self.getTokenCounts(con)
        self.df_market = self.getMarket(con)
        con.close()

    def add_data(self, timestamp: int, token: str, price: float, count: float):
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute(
            "INSERT INTO Database (timestamp, token, price, count) VALUES (?, ?, ?, ?)",
            (timestamp, token, price, count),
        )
        con.commit()
        con.close()

    def add_data_df(self, tokens: dict):
        logger.debug("Adding data to database")

        timestamp = int(pd.Timestamp.now().timestamp())

        df: pd.DataFrame = pd.DataFrame(
            columns=["timestamp", "token", "price", "count"]
        )
        for token, data in tokens.items():
            logger.debug(f"data: {data}")
            df.loc[len(df)] = [timestamp, token, data["price"], data["amount"]]
        logger.debug(f"Dataframe to add:\n{df}")
        con = sqlite3.connect(self.db_path)
        df.to_sql("Database", con, if_exists="append", index=False)
        con.close()
        self.makeDataframes()
