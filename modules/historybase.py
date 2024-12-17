import sqlite3
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class HistoryBase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.__initDatabase()

    def __initDatabase(self):
        logger.debug("Init database")
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS Database (timestamp INTEGER, token TEXT, price REAL, count REAL)"
            )
            con.commit()

    def getSums(self) -> pd.DataFrame:
        logger.debug("Get sums")
        with sqlite3.connect(self.db_path) as con:
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

    def getBalances(self) -> pd.DataFrame:
        logger.debug("Get balances")
        with sqlite3.connect(self.db_path) as con:
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

    def getTokenCounts(self) -> pd.DataFrame:
        logger.debug("Get token counts")
        with sqlite3.connect(self.db_path) as con:
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

    def getMarket(self) -> pd.DataFrame:
        logger.debug("Get market")
        with sqlite3.connect(self.db_path) as con:
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

    def add_data(self, timestamp: int, token: str, price: float, count: float):
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO Database (timestamp, token, price, count) VALUES (?, ?, ?, ?)",
                (timestamp, token, price, count),
            )
            con.commit()

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
        with sqlite3.connect(self.db_path) as con:
            df.to_sql("Database", con, if_exists="append", index=False)

    def get_last_timestamp(self) -> int:
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                "SELECT MAX(timestamp) as timestamp from Database;", con
            )
            return df["timestamp"][0]
        
    def get_last_timestamp_by_token(self, token: str) -> int:
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                f"SELECT MAX(timestamp) as timestamp from Database WHERE token = '{token}';", con
            )
            return df["timestamp"][0]
    
    def get_last_price(self, token: str) -> float:
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                f"SELECT price from Database WHERE token = '{token}' ORDER BY timestamp DESC LIMIT 1;", con
            )
            return df["price"][0]
        
    def dropDuplicate(self):
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query("SELECT * from Database;", con) 
            dupcount = df.duplicated().sum()
            logger.debug(f"Found {len(df)} rows with {dupcount} duplicated rows")
            if dupcount > 0:
                logger.debug(f"Found {dupcount} duplicated rows. Dropping...") 
                df.drop_duplicates(inplace=True)
                df.to_sql('Database', con, if_exists='replace', index=False)
