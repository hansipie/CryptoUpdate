"""MarketRaccoon API client module.

This module provides the ApiMarket class for interacting with the MarketRaccoon API
to fetch real-time fiat currency exchange rates. It handles API requests, data
formatting, and timezone conversions for financial data.
"""

import logging

import pandas as pd
import requests
import tzlocal

logger = logging.getLogger(__name__)


class ApiMarket:
    """Client for MarketRaccoon API to fetch fiat currency exchange rates.
    
    This class provides methods to interact with the MarketRaccoon API
    for retrieving real-time currency exchange rates.
    Attributes:
        url (str): Base URL of the MarketRaccoon API
        local_timezone: Local timezone for date conversion
    """

    def __init__(self, url: str):
        self.url = url
        self.local_timezone = tzlocal.get_localzone()

    def get_fiat_latest_rate(self) -> pd.DataFrame:
        """Get latest currency rates.

        Returns:
            DataFrame with currency rates or None if empty
        """
        logger.debug("Get currency")
        request = requests.get(
            self.url + "/api/v1/fiat/latest",
            timeout=10,
        )
        if request.status_code == 200:
            data = request.json()
            # L'API retourne un array, pas un objet
            if not data:  # Si la liste est vide
                return None

            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df["date"] = df["date"].dt.tz_convert(self.local_timezone)
            df.rename(columns={"date": "Date", "eur": "price"}, inplace=True)
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)

            return df
        if request.status_code == 204:
            # Pas de données disponibles
            logger.info("No fiat data available (204)")
            return None

        logger.error("Error fetching fiat rates: %s", request.status_code)
        return None
