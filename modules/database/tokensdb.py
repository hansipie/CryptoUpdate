import sqlite3
import pandas as pd
import logging
import tzlocal

logger = logging.getLogger(__name__)

class TokensDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.__init_database()
        self.local_timezone = tzlocal.get_localzone()

    def __init_database(self):
        logger.debug("Init database")
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS TokensDatabase (timestamp INTEGER, token TEXT, price REAL, count REAL)"
            )
            con.commit()

    def get_sums(self) -> pd.DataFrame:
        """Get the sum of all tokens through time"""
        logger.debug("Get sums")
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                "SELECT DISTINCT timestamp from TokensDatabase ORDER BY timestamp", con
            )
            df_sum = pd.DataFrame(columns=["timestamp", "value"])
            for mytime in df["timestamp"]:
                dftmp = pd.read_sql_query(
                    f"SELECT ROUND(sum(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END)), 2) as value, timestamp from TokensDatabase WHERE timestamp = {str(mytime)};",
                    con,
                )
                df_sum.loc[len(df_sum)] = [dftmp["timestamp"][0], dftmp["value"][0]]
            df_sum["timestamp"] = pd.to_datetime(
                df_sum["timestamp"], unit="s", utc=True
            )
            df_sum["timestamp"] = df_sum["timestamp"].dt.tz_convert(self.local_timezone)
            df_sum.rename(columns={"timestamp": "Date", "value" : "Sum"}, inplace=True)
            df_sum.set_index("Date", inplace=True)
            df_sum = df_sum.reindex(sorted(df_sum.columns), axis=1)
            return df_sum

    def getBalances(self) -> pd.DataFrame:
        """Get the balances of each token through time"""
        logger.debug("Get balances")
        with sqlite3.connect(self.db_path) as con:
            df_tokens = pd.read_sql_query("select DISTINCT token from TokensDatabase", con)
            logger.debug("Tokens:\n%s", df_tokens.to_string())
            if df_tokens.empty:
                logger.warning("No token found in database")
                return None
            df_balance = pd.DataFrame()
            for token in df_tokens["token"]:
                df = pd.read_sql_query(
                    f"SELECT timestamp, ROUND(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END), 2) AS '{token}' FROM TokensDatabase WHERE token = '{token}' ORDER BY timestamp;",
                    con,
                )
                if df_balance.empty:
                    df_balance = df
                else:
                    df_balance = df_balance.merge(df, on="timestamp", how="outer")
            df_balance = df_balance.fillna(0) # c'est OK de remplir les NaN ici
            df_balance["timestamp"] = pd.to_datetime(
                df_balance["timestamp"], unit="s", utc=True
            )
            df_balance["timestamp"] = df_balance["timestamp"].dt.tz_convert(
                self.local_timezone
            )
            df_balance.rename(columns={"timestamp": "Date"}, inplace=True)
            df_balance.set_index("Date", inplace=True)
            df_balance = df_balance.reindex(sorted(df_balance.columns), axis=1)
            return df_balance

    def getTokenCounts(self) -> pd.DataFrame:
        """Get the count of each token through time"""
        logger.debug("Get token counts")
        with sqlite3.connect(self.db_path) as con:
            df_tokens = pd.read_sql_query("select DISTINCT token from TokensDatabase", con)
            logger.debug("Tokens:\n%s", df_tokens.to_string())
            if df_tokens.empty:
                logger.warning("No token found in database")
                return None
            df_tokencount = pd.DataFrame()
            for token in df_tokens["token"]:
                df = pd.read_sql_query(
                    f"SELECT timestamp, count AS '{token}' FROM TokensDatabase WHERE token = '{token}' ORDER BY timestamp;",
                    con,
                )
                if df_tokencount.empty:
                    df_tokencount = df
                else:
                    df_tokencount = df_tokencount.merge(df, on="timestamp", how="outer")
            df_tokencount = df_tokencount.fillna(0) # c'est OK de remplir les NaN ici
            df_tokencount["timestamp"] = pd.to_datetime(
                df_tokencount["timestamp"], unit="s", utc=True
            )
            df_tokencount["timestamp"] = df_tokencount["timestamp"].dt.tz_convert(
                self.local_timezone
            )
            df_tokencount.rename(columns={"timestamp": "Date"}, inplace=True)
            df_tokencount.set_index("Date", inplace=True)
            df_tokencount = df_tokencount.reindex(sorted(df_tokencount.columns), axis=1)
            return df_tokencount

    def addToken(self, timestamp: int, token: str, price: float, count: float):
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO TokensDatabase (timestamp, token, price, count) VALUES (?, ?, ?, ?)",
                (timestamp, token, price, count),
            )
            con.commit()

    def addTokens(self, tokens: dict):
        logger.debug(f"Adding data to database:\n{tokens}")
        timestamp = int(pd.Timestamp.now(tz="UTC").timestamp())

        df: pd.DataFrame = pd.DataFrame(
            columns=["timestamp", "token", "price", "count"]
        )
        for token, data in tokens.items():
            if "timestamp" in data:
                df.loc[len(df)] = [
                    data["timestamp"],
                    token,
                    data["price"],
                    data["amount"],
                ]
            else:
                df.loc[len(df)] = [timestamp, token, data["price"], data["amount"]]
        logger.debug(f"Dataframe to add:\n{df}")
        with sqlite3.connect(self.db_path) as con:
            df.to_sql("TokensDatabase", con, if_exists="append", index=False)

    def get_last_timestamp(self) -> int:
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                "SELECT MAX(timestamp) as timestamp from TokensDatabase;", con
            )
            return df["timestamp"][0]

    def get_last_timestamp_by_token(self, token: str) -> int:
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                f"SELECT MAX(timestamp) as timestamp from TokensDatabase WHERE token = '{token}';",
                con,
            )
            return df["timestamp"][0]

    def dropDuplicate(self):
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query("SELECT * from TokensDatabase;", con)
            dupcount = df.duplicated().sum()
            logger.debug(f"Found {len(df)} rows with {dupcount} duplicated rows")
            if dupcount > 0:
                logger.debug(f"Found {dupcount} duplicated rows. Dropping...")
                df.drop_duplicates(inplace=True)
                df.to_sql("TokensDatabase", con, if_exists="replace", index=False)

    def getTokens(self) -> list:
        with sqlite3.connect(self.db_path) as con:
            df = pd.read_sql_query(
                "SELECT DISTINCT token from TokensDatabase ORDER BY token", con
            )
            return df["token"].to_list()
