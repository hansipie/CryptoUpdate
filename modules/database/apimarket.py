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

    def get_currency(self) -> pd.DataFrame:
        """Get historical currency rates.

        Returns:
            DataFrame with currency rates over time or None if empty
        """
        logger.debug("Get currency")
        request = requests.get(
            self.url + "/api/v1/fiat/all",
            timeout=10,
        )
        if request.status_code == 200:
            data = request.json()
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df["date"] = df["date"].dt.tz_convert(self.local_timezone)
            df.rename(columns={"date": "Date", "eur": "price"}, inplace=True)
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)

            # convert prices from EUR to USD
            # df["price"] = 1/df["price"]

            return df
        return None

    def get_currency_lowhigh(self, timestamp: int) -> pd.DataFrame:
        """Get the low and high currency rates for a given timestamp.

        Args:
            timestamp: The timestamp to get the rates for

        Returns:
            Two DataFrames with the low and high rates or None if empty
        """
        logger.debug("Get currency low and high")

        date = fromTimestamp(timestamp)

        request = requests.get(
            self.url + f"/api/v1/fiat?date={date}",
            timeout=10,
        )
        if request.status_code == 200:
            data = request.json()
            df = pd.DataFrame(data)
            df["timestamp"] = df.apply(
                lambda x: int(toTimestamp_B(x["date"], utc=True)), axis=1
            )
            df.sort_values("timestamp", inplace=True)

            df.rename(columns={"eur": "price"}, inplace=True)
            # convert prices from EUR to USD
            # df["price"] = 1/df["price"]

            logger.debug("Currency data:\n%s", df)

            if len(df) == 0:
                return None, None
            low_df = df[df["timestamp"] <= timestamp].iloc[-1:]
            high_df = df[df["timestamp"] >= timestamp].iloc[:1]

            logger.debug("Low Data:\n%s", low_df)
            logger.debug("High Data:\n%s", high_df)

            return low_df, high_df
        logger.error("Failed to get data, status code: %s", request.status_code)
        return None, None
