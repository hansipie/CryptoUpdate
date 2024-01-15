import os
import sqlite3
import pandas as pd
import streamlit as st

class Data:

    def __init__(self, db_path, version="2022-06-28"):
        self.db_path = db_path
        self.initDatabase()
        self.df_balance  = pd.DataFrame()
        self.df_tokencount  = pd.DataFrame()
        self.df_market  = pd.DataFrame()
        self.df_sum = pd.DataFrame()
        self.sum = self.make_data()

    def initDatabase(self):
        print("Init database", __file__, __name__)
        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS Database (timestamp INTEGER, token TEXT, price REAL, count REAL)")
        con.commit()
        con.close()

    def make_data(self):
        print("Make dataframes")

        con = sqlite3.connect(self.db_path)

        # sum
        df_temp = pd.read_sql_query("SELECT DISTINCT timestamp from Database ORDER BY timestamp", con)
        self.df_sum = pd.DataFrame(columns=['datetime', 'value'])
        for mytime in df_temp['timestamp']:
            dftmp = pd.read_sql_query("SELECT ROUND(sum(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END)), 2) as value, DATETIME(timestamp, 'unixepoch') AS datetime from Database WHERE timestamp = " + str(mytime), con)
            self.df_sum.loc[len(self.df_sum)] = [dftmp['datetime'][0], dftmp['value'][0]]
        self.df_sum.set_index('datetime', inplace=True)

        # balances
        df_tokens = pd.read_sql_query("select DISTINCT token from Database", con)
        for token in df_tokens['token']:
            df = pd.read_sql_query(f"SELECT DATETIME(timestamp, 'unixepoch') AS datetime, ROUND(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END), 2) AS {token} FROM Database WHERE token = '"+token+"' ORDER BY timestamp;", con)
            df.set_index('datetime', inplace=True)
            self.df_balance = pd.concat([self.df_balance, df], axis=1)   

            df = pd.read_sql_query(f"SELECT DATETIME(timestamp, 'unixepoch') AS datetime, count AS {token} FROM Database WHERE token = '"+token+"' ORDER BY timestamp;", con)
            df.set_index('datetime', inplace=True)
            self.df_tokencount = pd.concat([self.df_tokencount, df], axis=1)   

            df = pd.read_sql_query(f"SELECT DATETIME(timestamp, 'unixepoch') AS datetime, price AS {token} FROM Database WHERE token = '"+token+"' ORDER BY timestamp;", con)
            df.set_index('datetime', inplace=True)
            self.df_market = pd.concat([self.df_market, df], axis=1)   

        self.df_balance = self.df_balance.fillna(0)
        self.df_tokencount = self.df_tokencount.fillna(0)
        self.df_market = self.df_market.fillna(0)

        self.df_balance.sort_index()
        self.df_tokencount.sort_index()
        self.df_market.sort_index()

        con.close()
        print("Dataframes loaded")
