"""MarketRaccoon API client module.

This module provides the ApiMarket class for interacting with the MarketRaccoon API
to fetch real-time fiat currency exchange rates. It handles API requests, data
formatting, and timezone conversions for financial data.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests
import tzlocal
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from modules.database.fiat_cache import FiatCacheManager

logger = logging.getLogger(__name__)

_SOURCE_CURRENCY = "USD"
_MAX_PAGES = 1000
_TIMEOUT = 10
# Taille de page maximale acceptée par l'API (au-delà elle plafonne à 10000)
_PAGE_SIZE = 10000
_RETRY_STATUS = (429, 500, 502, 503, 504)


class ApiMarket:
    """Client for MarketRaccoon API to fetch fiat currency exchange rates.

    This class provides methods to interact with the MarketRaccoon API
    for retrieving real-time currency exchange rates.

    Attributes:
        url (str): Base URL of the MarketRaccoon API
        api_key (str): API key for authentication
        local_timezone: Local timezone for date conversion
        cache (FiatCacheManager): Optional cache manager for API responses
    """

    def __init__(self, url: str, api_key: str = None, cache_file: Optional[str] = None):
        """Initialize ApiMarket client.

        Args:
            url: Base URL of the MarketRaccoon API
            api_key: API key for authentication (optional)
            cache_file: Optional path to cache file. If provided, enables caching.
        """
        # Remove trailing slash from URL if present
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.local_timezone = tzlocal.get_localzone()
        self.cache = FiatCacheManager(cache_file) if cache_file else None
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        """Create an HTTP session with keep-alive, API key header and retries.

        Retries (with exponential backoff, honouring Retry-After) apply to
        transient failures: 429, 5xx and connection errors.
        """
        session = requests.Session()
        if self.api_key:
            session.headers["X-API-Key"] = self.api_key
        # read=0 : pas de nouvel essai après un timeout de lecture, sinon un
        # endpoint lent (ex. /cryptocurrency/latest sans filtre) bloque 4x le timeout.
        retry = Retry(
            total=3,
            read=0,
            backoff_factor=0.5,
            status_forcelist=_RETRY_STATUS,
            allowed_methods=("GET",),
            respect_retry_after_header=True,
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.mount("http://", HTTPAdapter(max_retries=retry))
        return session

    def _get(self, url: str, params: Optional[dict] = None) -> Optional[requests.Response]:
        """GET a URL with the shared session.

        Args:
            url: Absolute URL
            params: Optional query parameters

        Returns:
            The response, or None if the request failed after retries
        """
        try:
            return self.session.get(url, params=params, timeout=_TIMEOUT)
        except requests.exceptions.RequestException as e:
            logger.error("API request failed: %s", e)
            return None

    def _get_paginated(self, path: str, params: Optional[dict] = None) -> Optional[list]:
        """Fetch every page of a paginated endpoint.

        Args:
            path: Endpoint path (e.g. "/api/v1/fiat")
            params: Query parameters for the first request ("next" URLs carry
                their own)

        Returns:
            List of all results, or None on error / no content (204)
        """
        query = dict(params or {})
        query["page_size"] = _PAGE_SIZE
        next_url = self.url + path
        all_results = []
        pages_fetched = 0
        while next_url and pages_fetched < _MAX_PAGES:
            logger.debug("Fetching page: %s", next_url)
            response = self._get(next_url, params=query if pages_fetched == 0 else None)
            if response is None:
                return None
            pages_fetched += 1

            if response.status_code == 200:
                data = response.json()
                all_results.extend(data.get("results", []))
                next_url = data.get("next")
            elif response.status_code == 204:
                logger.info("No content (204) for %s", path)
                return None
            else:
                logger.error("Error fetching %s: %s", path, response.status_code)
                return None

        if pages_fetched >= _MAX_PAGES:
            logger.warning("Pagination limit reached for %s", path)
        return all_results

    def get_fiat_latest_rate(self) -> pd.DataFrame:
        """Get latest currency rates.

        Returns:
            DataFrame with currency rates or None if empty
        """
        logger.debug("Get currency")
        response = self._get(self.url + "/api/v1/fiat/latest")
        if response is None:
            return None
        if response.status_code == 200:
            data = response.json()
            # L'API retourne un array, pas un objet
            if not data:  # Si la liste est vide
                return None

            # L'API retourne un objet unique, créer une liste pour DataFrame
            df = pd.DataFrame([data])
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df["date"] = (
                df["date"].dt.tz_convert(self.local_timezone).dt.tz_localize(None)
            )
            df = df.rename(columns={"date": "Date", "eur": "price"})
            df = df.set_index("Date")
            df = df.sort_index()

            return df
        if response.status_code == 204:
            # Pas de données disponibles
            logger.info("No fiat data available (204)")
            return None

        logger.error("Error fetching fiat rates: %s", response.status_code)
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
            "fiat_latest", self._fetch_and_serialize_latest_rate
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
            "interpolated": False,
        }

    def _deserialize_latest_rate(self, cached_data: dict) -> pd.DataFrame:
        """Deserialize cached data back to DataFrame.

        Args:
            cached_data: Serialized rate data from cache

        Returns:
            DataFrame with same structure as get_fiat_latest_rate()
        """
        # Reconstruct DataFrame from cached dict
        df = pd.DataFrame(
            [
                {
                    "Date": pd.to_datetime(cached_data["date"], utc=True)
                    .tz_convert(self.local_timezone)
                    .tz_localize(None),
                    "price": cached_data["price"],
                }
            ]
        )

        df = df.set_index("Date")
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
            dt = datetime.fromtimestamp(timestamp, tz=self.local_timezone)
            date_str = dt.astimezone(timezone.utc).isoformat()

            response = self._get(self.url + "/api/v1/fiat", params={"date": date_str})
            if response is None:
                return None

            if response.status_code == 200:
                results = response.json().get("results", [])

                if not results:
                    logger.info("No fiat data available for timestamp %d", timestamp)
                    return None

                df = pd.DataFrame(results)
                df["date"] = pd.to_datetime(df["date"], utc=True)
                df["date"] = (
                    df["date"].dt.tz_convert(self.local_timezone).dt.tz_localize(None)
                )
                df = df.rename(columns={"date": "Date", "eur": "price"})
                df = df.set_index("Date")

                logger.info(
                    "Retrieved interpolated fiat rate for timestamp %d", timestamp
                )
                return df
            if response.status_code == 204:
                logger.info("No fiat data available (204)")
                return None
            logger.error("Error fetching fiat data: %s", response.status_code)
            return None

        # Otherwise, fetch all data with pagination
        logger.debug("Get all fiat currency data")
        all_results = self._get_paginated("/api/v1/fiat")
        if not all_results:
            logger.info("No fiat data retrieved")
            return None

        df = pd.DataFrame(all_results)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df["date"] = df["date"].dt.tz_convert(self.local_timezone).dt.tz_localize(None)
        df = df.rename(columns={"date": "Date", "eur": "price"})
        df = df.set_index("Date")
        df = df.sort_index()

        logger.info("Retrieved %d total fiat records", len(df))
        return df

    def get_currency_cached(self) -> Optional[pd.DataFrame]:
        """Get the full fiat history with caching support.

        Falls back to a direct API call when the cache is disabled.

        Returns:
            DataFrame with columns: Date (index), price, interpolated
        """
        if not self.cache:
            return self.get_currency()

        cached_data = self.cache.get_or_fetch(
            "fiat_history", self._fetch_and_serialize_fiat_history
        )
        if cached_data is None:
            return None

        df = pd.DataFrame(cached_data["records"])
        df["Date"] = pd.to_datetime(df["Date"], format="ISO8601")
        return df.set_index("Date").sort_index()

    def _fetch_and_serialize_fiat_history(self) -> Optional[dict]:
        """Fetch the full fiat history from API and serialize for caching."""
        df = self.get_currency()
        if df is None or df.empty:
            return None
        out = df.reset_index()
        out["Date"] = out["Date"].map(lambda d: d.isoformat())
        return {"records": out.to_dict(orient="records")}

    def get_coins(self, symbols: list = None) -> pd.DataFrame:
        """Get list of coins from the API.

        Args:
            symbols: Optional list of symbols to filter

        Returns:
            DataFrame with coin information (id, symbol, name)
            Returns None if no data is available or an error occurs
        """
        logger.debug("Get coins list")

        params = {}
        if symbols:
            params["symbols"] = ",".join(symbols)

        results = self._get_paginated("/api/v1/coins", params)
        if not results:
            logger.info("No coins available")
            return None
        return pd.DataFrame(results)

    def get_cryptocurrency_market(
        self,
        coinid: int = None,
        token_symbol: str = None,
        from_timestamp: int = None,
        to_timestamp: int = None,
    ) -> pd.DataFrame:
        """Get cryptocurrency market data from the API.

        Args:
            coinid: Optional coin ID to filter
            token_symbol: Optional token symbol (will fetch coinid first)
            from_timestamp: Optional Unix timestamp for start date
            to_timestamp: Optional Unix timestamp for end date

        Returns:
            DataFrame with columns: Date (index), Price
            Returns None if no data is available or an error occurs
        """
        # If token_symbol provided, get coinid first
        if token_symbol and not coinid:
            coins_df = self.get_coins(symbols=[token_symbol])
            if coins_df is None or coins_df.empty:
                logger.warning("Token %s not found in API", token_symbol)
                return None
            coinid = coins_df.iloc[0]["id"]
            logger.debug("Found coinid %d for token %s", coinid, token_symbol)

        if not coinid:
            logger.error("coinid or token_symbol required")
            return None

        logger.debug("Get cryptocurrency market data for coinid: %d", coinid)

        # Build query parameters
        params = {"coinid": coinid}
        if from_timestamp:
            dt = datetime.fromtimestamp(from_timestamp, tz=self.local_timezone)
            params["startdate"] = dt.astimezone(timezone.utc).isoformat()
        if to_timestamp:
            dt = datetime.fromtimestamp(to_timestamp, tz=self.local_timezone)
            params["enddate"] = dt.astimezone(timezone.utc).isoformat()

        all_results = self._get_paginated("/api/v1/cryptocurrency", params)
        if not all_results:
            logger.info("No cryptocurrency data retrieved")
            return None

        df = pd.DataFrame(all_results)
        df["last_updated"] = pd.to_datetime(
            df["last_updated"], format="ISO8601", utc=True
        )
        df["last_updated"] = (
            df["last_updated"].dt.tz_convert(self.local_timezone).dt.tz_localize(None)
        )
        df = df.rename(columns={"last_updated": "Date", "price": "Price"})
        df["source_currency"] = _SOURCE_CURRENCY  # MÉTADONNÉE : Prix en USD
        if "interpolated" not in df.columns:
            df["interpolated"] = False
        df["interpolated"] = df["interpolated"].fillna(False).astype(bool)
        df = df[["Date", "Price", "source_currency", "interpolated"]]
        df = df.set_index("Date")
        df = df.sort_index()

        logger.info("Retrieved %d total cryptocurrency records", len(df))
        return df

    def get_coins_cached(self, symbols: list = None) -> Optional[pd.DataFrame]:
        """Get list of coins with caching support.

        This is the cached version of get_coins(). If cache is disabled
        (cache_file=None), falls back to direct API call.

        Args:
            symbols: Optional list of symbols to filter

        Returns:
            DataFrame with coin information or None if empty
        """
        if not self.cache:
            return self.get_coins(symbols)

        # Create cache key based on symbols
        if symbols:
            symbols_key = "_".join(sorted(symbols))
            cache_key = f"coins_{symbols_key}"
        else:
            cache_key = "coins"

        cached_data = self.cache.get_or_fetch(
            cache_key, lambda: self._fetch_and_serialize_coins(symbols)
        )

        if cached_data is None:
            return None

        return self._deserialize_coins(cached_data)

    def _fetch_and_serialize_coins(self, symbols: list = None) -> Optional[dict]:
        """Fetch coins from API and serialize for caching.

        Args:
            symbols: Optional list of symbols to filter

        Returns:
            Serialized coins data dict or None if fetch failed
        """
        df = self.get_coins(symbols)

        if df is None or df.empty:
            return None

        # Serialize DataFrame to cacheable dict
        return {"records": df.to_dict(orient="records")}

    def _deserialize_coins(self, cached_data: dict) -> pd.DataFrame:
        """Deserialize cached coins data back to DataFrame.

        Args:
            cached_data: Serialized coins data from cache

        Returns:
            DataFrame with same structure as get_coins()
        """
        return pd.DataFrame(cached_data["records"])

    def get_cryptocurrency_market_cached(
        self,
        coinid: int = None,
        token_symbol: str = None,
        from_timestamp: int = None,
        to_timestamp: int = None,
    ) -> Optional[pd.DataFrame]:
        """Get cryptocurrency market data with caching support.

        This is the cached version of get_cryptocurrency_market(). If cache is disabled
        (cache_file=None), falls back to direct API call.

        Args:
            coinid: Optional coin ID to filter
            token_symbol: Optional token symbol (will fetch coinid first)
            from_timestamp: Optional Unix timestamp for start date
            to_timestamp: Optional Unix timestamp for end date

        Returns:
            DataFrame with columns: Date (index), Price or None if empty
        """
        if not self.cache:
            return self.get_cryptocurrency_market(
                coinid, token_symbol, from_timestamp, to_timestamp
            )

        # Resolve token_symbol to coinid if needed (use cached coins)
        if token_symbol and not coinid:
            coins_df = self.get_coins_cached(symbols=[token_symbol])
            if coins_df is None or coins_df.empty:
                logger.warning("Token %s not found in API", token_symbol)
                return None
            coinid = coins_df.iloc[0]["id"]
            logger.debug("Found coinid %d for token %s", coinid, token_symbol)

        if not coinid:
            logger.error("coinid or token_symbol required")
            return None

        # Create cache key based on parameters
        cache_key = f"crypto_{coinid}_{from_timestamp or 0}_{to_timestamp or 0}"

        cached_data = self.cache.get_or_fetch(
            cache_key,
            lambda: self._fetch_and_serialize_crypto_market(
                coinid, from_timestamp, to_timestamp
            ),
        )

        if cached_data is None:
            return None

        return self._deserialize_crypto_market(cached_data)

    def _fetch_and_serialize_crypto_market(
        self, coinid: int, from_timestamp: int = None, to_timestamp: int = None
    ) -> Optional[dict]:
        """Fetch cryptocurrency market data from API and serialize for caching.

        Args:
            coinid: Coin ID to fetch
            from_timestamp: Optional Unix timestamp for start date
            to_timestamp: Optional Unix timestamp for end date

        Returns:
            Serialized market data dict or None if fetch failed
        """
        df = self.get_cryptocurrency_market(
            coinid=coinid, from_timestamp=from_timestamp, to_timestamp=to_timestamp
        )

        if df is None or df.empty:
            return None

        # Serialize DataFrame to cacheable dict
        # Convert datetime index to ISO strings
        records = []
        for date, row in df.iterrows():
            records.append(
                {
                    "date": date.isoformat(),
                    "price": float(row["Price"]),
                    "interpolated": bool(row.get("interpolated", False)),
                }
            )

        # Préserver la métadonnée de devise source
        source_currency = (
            df["source_currency"].iloc[0] if "source_currency" in df.columns else "USD"
        )

        return {"records": records, "source_currency": source_currency}

    def _deserialize_crypto_market(self, cached_data: dict) -> pd.DataFrame:
        """Deserialize cached cryptocurrency market data back to DataFrame.

        Args:
            cached_data: Serialized market data from cache

        Returns:
            DataFrame with same structure as get_cryptocurrency_market()
        """
        records = cached_data["records"]

        # Reconstruct DataFrame
        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"], format="ISO8601")
        df = df.rename(columns={"date": "Date", "price": "Price"})
        if "interpolated" not in df.columns:  # anciens caches
            df["interpolated"] = False
        # Restaurer la métadonnée de devise source (USD par défaut pour rétrocompatibilité cache)
        df["source_currency"] = cached_data.get("source_currency", _SOURCE_CURRENCY)
        df = df.set_index("Date")
        df = df.sort_index()

        return df

    def get_cryptocurrency_latest_cached(self) -> Optional[pd.DataFrame]:
        """Get latest cryptocurrency market data with caching support.

        This is the cached version of get_cryptocurrency_latest(). If cache is disabled
        (cache_file=None), falls back to direct API call.

        Returns:
            DataFrame with latest market data or None if empty
        """
        if not self.cache:
            return self.get_cryptocurrency_latest()

        cached_data = self.cache.get_or_fetch(
            "crypto_latest", self._fetch_and_serialize_latest
        )

        if cached_data is None:
            return None

        return self._deserialize_latest(cached_data)

    def _fetch_and_serialize_latest(self) -> Optional[dict]:
        """Fetch latest cryptocurrency data from API and serialize for caching.

        Returns:
            Serialized latest data dict or None if fetch failed
        """
        df = self.get_cryptocurrency_latest()

        if df is None or df.empty:
            return None

        records = []
        for date, row in df.iterrows():
            records.append(
                {
                    "date": date.isoformat(),
                    "coin": int(row["coin"]),
                    "price": float(row["price"]),
                }
            )

        return {"records": records}

    def _deserialize_latest(self, cached_data: dict) -> pd.DataFrame:
        """Deserialize cached latest cryptocurrency data back to DataFrame.

        Args:
            cached_data: Serialized latest data from cache

        Returns:
            DataFrame with same structure as get_cryptocurrency_latest()
        """
        df = pd.DataFrame(cached_data["records"])
        df["date"] = pd.to_datetime(df["date"], format="ISO8601")
        df = df.rename(columns={"date": "Date"})
        df = df.set_index("Date")
        return df

    def get_cryptocurrency_latest(self, symbols: list = None) -> pd.DataFrame:
        """Get latest cryptocurrency market data for all coins.

        Args:
            symbols: Optional list of token symbols to filter (e.g., ['BTC', 'ETH']).
                    When provided, uses API's symbol filter to avoid duplicate symbols.

        Returns:
            DataFrame with latest market data
            Returns None if no data is available or an error occurs
        """
        logger.debug("Get latest cryptocurrency data")
        params = {}
        if symbols:
            # Use API's symbol filter to get the canonical tokens
            params["symbols"] = ",".join(symbols)
            logger.debug("Filtering by symbols: %s", params["symbols"])

        response = self._get(self.url + "/api/v1/cryptocurrency/latest", params=params)
        if response is None:
            return None

        if response.status_code == 200:
            data = response.json()

            if not data:
                logger.info("No latest cryptocurrency data available")
                return None

            df = pd.DataFrame(data)
            # L'API renvoie "coin" comme objet {id, symbol, ...} : on le réduit
            # à son id (les appelants et le cache attendent un entier).
            if df["coin"].map(lambda c: isinstance(c, dict)).any():
                df["symbol"] = df["coin"].map(
                    lambda c: c.get("symbol") if isinstance(c, dict) else None
                )
                df["coin"] = df["coin"].map(
                    lambda c: c["id"] if isinstance(c, dict) else c
                )
            df["last_updated"] = pd.to_datetime(
                df["last_updated"], format="ISO8601", utc=True
            )
            # Sort by last_updated and drop duplicates to ensure only the latest price per coin is kept
            df = df.sort_values(by="last_updated", ascending=False)
            df = df.drop_duplicates(subset="coin", keep="first")
            df["last_updated"] = (
                df["last_updated"]
                .dt.tz_convert(self.local_timezone)
                .dt.tz_localize(None)
            )
            df = df.rename(columns={"last_updated": "Date"})
            df = df.set_index("Date")

            logger.info("Retrieved %d latest cryptocurrency records", len(df))
            return df
        elif response.status_code == 204:
            logger.info("No latest cryptocurrency data available (204)")
            return None
        else:
            logger.error(
                "Error fetching latest cryptocurrency data: %s", response.status_code
            )
            return None
