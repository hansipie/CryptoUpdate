"""MarketRaccoon API client module.

This module provides the ApiMarket class for interacting with the MarketRaccoon API
to fetch real-time fiat currency exchange rates. It handles API requests, data
formatting, and timezone conversions for financial data.
"""

import logging
from typing import Optional

import pandas as pd
import requests
import tzlocal

from modules.database.fiat_cache import FiatCacheManager

logger = logging.getLogger(__name__)


class ApiMarket:
    """Client for MarketRaccoon API to fetch fiat currency exchange rates.

    This class provides methods to interact with the MarketRaccoon API
    for retrieving real-time currency exchange rates.

    Attributes:
        url (str): Base URL of the MarketRaccoon API
        local_timezone: Local timezone for date conversion
        cache (FiatCacheManager): Optional cache manager for API responses
    """

    def __init__(self, url: str, cache_file: Optional[str] = None):
        """Initialize ApiMarket client.

        Args:
            url: Base URL of the MarketRaccoon API
            cache_file: Optional path to cache file. If provided, enables caching.
        """
        self.url = url
        self.local_timezone = tzlocal.get_localzone()
        self.cache = FiatCacheManager(cache_file) if cache_file else None

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

            # L'API retourne un objet unique, créer une liste pour DataFrame
            df = pd.DataFrame([data])
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df["date"] = df["date"].dt.tz_convert(self.local_timezone).dt.tz_localize(None)
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

    def get_fiat_latest_rate_cached(self) -> Optional[pd.DataFrame]:
        """Get latest currency rates with caching support.

        This is the cached version of get_fiat_latest_rate(). If cache is disabled
        (cache_file=None), falls back to direct API call.

        Returns:
            DataFrame with currency rates or None if empty
        """
        if not self.cache:
            # Cache disabled, use direct API call
            return self.get_fiat_latest_rate()

        # Use cache with fallback strategy
        cached_data = self.cache.get_or_fetch(
            "fiat_latest",
            self._fetch_and_serialize_latest_rate
        )

        if cached_data is None:
            return None

        return self._deserialize_latest_rate(cached_data)

    def _fetch_and_serialize_latest_rate(self) -> Optional[dict]:
        """Fetch latest rate from API and serialize for caching.

        Returns:
            Serialized rate data dict or None if fetch failed
        """
        df = self.get_fiat_latest_rate()

        if df is None or df.empty:
            return None

        # Serialize DataFrame to cacheable dict
        return {
            "date": df.index[0].isoformat(),
            "price": float(df.iloc[0]["price"]),
            "interpolated": False
        }

    def _deserialize_latest_rate(self, cached_data: dict) -> pd.DataFrame:
        """Deserialize cached data back to DataFrame.

        Args:
            cached_data: Serialized rate data from cache

        Returns:
            DataFrame with same structure as get_fiat_latest_rate()
        """
        # Reconstruct DataFrame from cached dict
        df = pd.DataFrame([{
            "Date": pd.to_datetime(cached_data["date"], utc=True).tz_convert(self.local_timezone).tz_localize(None),
            "price": cached_data["price"]
        }])

        df.set_index("Date", inplace=True)
        return df

    def get_currency(self, timestamp: int = None) -> pd.DataFrame:
        """Get fiat currency exchange rates from the API.

        If timestamp is provided, fetches the interpolated rate for that specific
        date. Otherwise, fetches all historical fiat exchange rate data with
        pagination.

        Args:
            timestamp: Optional Unix timestamp. If provided, returns interpolated
                      rate for that specific date. If None, returns all data.

        Returns:
            DataFrame with columns: Date (index), price, interpolated
            Returns None if no data is available or an error occurs
        """
        # If timestamp provided, fetch interpolated value for that date
        if timestamp is not None:
            logger.debug("Get fiat currency data for timestamp: %d", timestamp)

            # Convert Unix timestamp to ISO 8601 format
            from datetime import datetime
            dt = datetime.fromtimestamp(timestamp, tz=self.local_timezone)
            date_str = dt.astimezone(pd.Timestamp.now(tz='UTC').tz).isoformat()

            request = requests.get(
                self.url + "/api/v1/fiat",
                params={"date": date_str},
                timeout=10,
            )

            if request.status_code == 200:
                data = request.json()
                results = data.get("results", [])

                if not results:
                    logger.info("No fiat data available for timestamp %d", timestamp)
                    return None

                df = pd.DataFrame(results)
                df["date"] = pd.to_datetime(df["date"], utc=True)
                df["date"] = df["date"].dt.tz_convert(self.local_timezone).dt.tz_localize(None)
                df.rename(columns={"date": "Date", "eur": "price"}, inplace=True)
                df.set_index("Date", inplace=True)

                logger.info("Retrieved interpolated fiat rate for timestamp %d", timestamp)
                return df
            elif request.status_code == 204:
                logger.info("No fiat data available (204)")
                return None
            else:
                logger.error("Error fetching fiat data: %s", request.status_code)
                return None

        # Otherwise, fetch all data with pagination
        logger.debug("Get all fiat currency data")
        all_results = []
        next_url = self.url + "/api/v1/fiat"

        # Fetch all pages
        while next_url:
            logger.debug("Fetching page: %s", next_url)
            request = requests.get(next_url, timeout=10)

            if request.status_code == 200:
                data = request.json()
                results = data.get("results", [])
                all_results.extend(results)

                # Get next page URL
                next_url = data.get("next")

                logger.debug(
                    "Retrieved %d records, total so far: %d",
                    len(results),
                    len(all_results),
                )
            elif request.status_code == 204:
                logger.info("No fiat data available (204)")
                return None
            else:
                logger.error("Error fetching fiat data: %s", request.status_code)
                return None

        # Convert to DataFrame
        if not all_results:
            logger.info("No fiat data retrieved")
            return None

        df = pd.DataFrame(all_results)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df["date"] = df["date"].dt.tz_convert(self.local_timezone).dt.tz_localize(None)
        df.rename(columns={"date": "Date", "eur": "price"}, inplace=True)
        df.set_index("Date", inplace=True)
        df.sort_index(inplace=True)

        logger.info("Retrieved %d total fiat records", len(df))
        return df