import sqlite3
import pandas as pd
import logging

logger = logging.getLogger(__name__)
class Data:
    def __init__(self, db_path: str = "./data/db.sqlite3"):
        self.db_path = db_path
        self.initDatabase()
        self.df_balance = pd.DataFrame()
        self.df_tokencount = pd.DataFrame()
        self.df_market = pd.DataFrame()
        self.df_sum = pd.DataFrame()
        self.make_data()

    def initDatabase(self):
        logger.debug("Init database")
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS Database (timestamp INTEGER, token TEXT, price REAL, count REAL)"
        )
        con.commit()
        con.close()

    def make_data(self):
        logger.debug("Make dataframes")

        con = sqlite3.connect(self.db_path)

        # sum
        df_temp = pd.read_sql_query(
            "SELECT DISTINCT timestamp from Database ORDER BY timestamp", con
        )
        self.df_sum = pd.DataFrame(columns=["datetime", "value"])
        for mytime in df_temp["timestamp"]:
            dftmp = pd.read_sql_query(
                f"SELECT ROUND(sum(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END)), 2) as value, DATETIME(timestamp, 'unixepoch') AS datetime from Database WHERE timestamp = {str(mytime)};",
                con,
            )
            self.df_sum.loc[len(self.df_sum)] = [
                dftmp["datetime"][0],
                dftmp["value"][0],
            ]
        self.df_sum.set_index("datetime", inplace=True)

        # balances
        df_tokens = pd.read_sql_query("select DISTINCT token from Database", con)
        for token in df_tokens["token"]:
            df = pd.read_sql_query(
                f"SELECT DATETIME(timestamp, 'unixepoch') AS datetime, ROUND(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END), 2) AS '{token}' FROM Database WHERE token = '{token}' ORDER BY timestamp;",
                con,
            )
            df.set_index("datetime", inplace=True)
            if self.df_balance.empty:
                self.df_balance = df
            else:
                self.df_balance = self.df_balance.join(df, how="outer")

            df = pd.read_sql_query(
                f"SELECT DATETIME(timestamp, 'unixepoch') AS datetime, count AS '{token}' FROM Database WHERE token = '{token}' ORDER BY timestamp;",
                con,
            )
            df.set_index("datetime", inplace=True)
            if self.df_tokencount.empty:
                self.df_tokencount = df
            else:
                self.df_tokencount = self.df_tokencount.join(df, how="outer")

            df = pd.read_sql_query(
                f"SELECT DATETIME(timestamp, 'unixepoch') AS datetime, price AS '{token}' FROM Database WHERE token = '{token}' ORDER BY timestamp;",
                con,
            )
            df.set_index("datetime", inplace=True)
            if self.df_market.empty:
                self.df_market = df
            else:
                self.df_market = self.df_market.join(df, how="outer")

        self.df_balance = self.df_balance.fillna(0)
        self.df_tokencount = self.df_tokencount.fillna(0)
        self.df_market = self.df_market.fillna(0)

        self.df_balance.sort_index()
        self.df_tokencount.sort_index()
        self.df_market.sort_index()

        con.close()
        logger.debug("Dataframes loaded")
