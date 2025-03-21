import logging

import pandas as pd
import requests
import tzlocal

from modules.utils import fromTimestamp, toTimestamp_B

logger = logging.getLogger(__name__)


class ApiMarket:
    def __init__(self, url: str):
        self.url = url
        self.local_timezone = tzlocal.get_localzone()

    def __get_currency(self, url: str):
        logger.debug("Get currency from private method")
        logger.debug("URL: %s", url)
        request = requests.get(url, timeout=10, )
        if request.status_code == 200:
            data = request.json()
            results = data.get("results", [])
            next_url = data.get("next", None)
            return results, next_url
        return None, None

    def get_currency(self) -> pd.DataFrame:
        """Get historical currency rates.

        Returns:
            DataFrame with currency rates over time or None if empty
        """
        logger.debug("Get currency")
        url = self.url + "/api/v1/fiat"
        df = pd.DataFrame()
        while True:
            results, next_url = self.__get_currency(url)
            if not results:
                logger.debug("No data found in the response")
                continue
            df_tmp = pd.DataFrame(results)
            df = pd.concat([df, df_tmp], ignore_index=True)
            if next_url:
                url = next_url
            else:
                break

        if len(df) == 0:
            return None
        
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df["date"] = df["date"].dt.tz_convert(self.local_timezone)
        df.rename(columns={"date": "Date", "eur": "price"}, inplace=True)
        df.set_index("Date", inplace=True)
        df.sort_index(inplace=True)
        
        return df

    def __extend_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extend the DataFrame."""
        logger.debug("Extend DataFrame")
        if df is None or len(df) == 0:
            return None
        df["timestamp"] = df.apply(
            lambda x: int(toTimestamp_B(x["date"], utc=True)), axis=1
        )
        df.rename(columns={"eur": "price"}, inplace=True)

        logger.debug("extended df:\n%s", df)
        return df

    def get_currency_lowhigh(self, timestamp: int):
        """Get the low and high currency rates for a given timestamp.

        Args:
            timestamp: The timestamp to get the rates for

        Returns:
            Two DataFrames with the low and high rates or None if empty
        """
        logger.debug("Get currency low and high")

        date = fromTimestamp(timestamp)
        logger.debug("timestamp: %i -> Date: %s", timestamp, date)

        request = requests.get(
            self.url + f"/api/v1/fiat?date={date}",
            timeout=10,
        )
        if request.status_code == 200:
            data = request.json()
            if "results" not in data:
                logger.error("No results found in the response")
                return None, None
            df_data = pd.DataFrame(data.get("results", []))
            
            # reformating the dataframe
            df_data["timestamp"] = df_data.apply(
                lambda x: int(toTimestamp_B(x["date"], utc=True)), axis=1
            )
            df_data.rename(columns={"eur": "price"}, inplace=True)
            logger.debug("fiat data:\n%s", df_data)

            df_low = df_data[df_data['timestamp'] == df_data['timestamp'].min()]
            df_high = df_data[df_data['timestamp'] == df_data['timestamp'].max()]
            logger.debug("Low Data:\n%s", df_low)
            logger.debug("High Data:\n%s", df_high)

            return df_low, df_high
        logger.error("Failed to get data, status code: %s", request.status_code)
        return None, None
