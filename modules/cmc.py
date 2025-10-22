from datetime import datetime
import logging
import traceback
import pytz
import requests

logger = logging.getLogger(__name__)


class cmc:
    def __init__(self, coinmarketcap_token: str) -> dict:
        self.coinmarketcap_token = coinmarketcap_token

    def get_current_fiat_prices(
        self, converts: list = None, symbol="EUR", amount=1, debug=False
    ) -> dict:
        """
        Get the price of the fiat currencies from the Coinmarketcap API
        """

        if converts is None:
            converts = ["USD"]

        logger.debug("Get current maket prices form Coinmarketcap for:\n%s", converts)
        names = str(",").join(converts)
        logger.info("Request fiat current prices for %s", names)
        if debug:
            logger.info(
                "Debug mode: use sandbox-api.coinmarketcap.com instead of pro-api.coinmarketcap.com"
            )
            url = "https://sandbox-api.coinmarketcap.com/v2/tools/price-conversion"
            # In debug mode, use the sandbox API with the provided token
            # Sandbox API keys should be configured in settings
            headers = {"X-CMC_PRO_API_KEY": str(self.coinmarketcap_token)}
        else:
            url = "https://pro-api.coinmarketcap.com/v2/tools/price-conversion"
            headers = {"X-CMC_PRO_API_KEY": str(self.coinmarketcap_token)}

        params = {
            "amount": amount,
            "symbol": symbol,
            "convert": names,
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            fiat_prices = {}
            content = response.json()
            logger.info("Get current market prices from Coinmarketcap successfully")
            logger.debug("API response data: %s", content)
            for fiat in converts:
                # Initialiser l'entrée pour chaque token
                fiat_prices[fiat] = {"price": 0, "timestamp": 0}
                try:
                    logger.debug(
                        "Price for %s: %s", fiat, content["data"][0]["quote"][fiat]
                    )
                    price_data = content["data"][0]["quote"][fiat]["price"]
                    timestamp_data = content["data"][0]["quote"][fiat]["last_updated"]

                    if price_data is not None:
                        fiat_prices[fiat]["price"] = price_data
                        utc_time = datetime.strptime(
                            timestamp_data, "%Y-%m-%dT%H:%M:%S.%fZ"
                        )
                        fiat_prices[fiat]["timestamp"] = utc_time.replace(
                            tzinfo=pytz.UTC
                        ).timestamp()

                except (KeyError, IndexError, TypeError) as e:
                    logger.error("Error getting price for %s : %s", fiat, str(e))
                    traceback.print_exc()
                    logger.debug("Data received: %s", content["data"])
                    return None
            return fiat_prices
        else:
            logger.error("API request failed with status code: %d", response.status_code)
            logger.debug("Error response: %s", response.text)
            return None

    def get_crypto_prices(self, tokens: list, unit="EUR", debug=False):
        """
        Get the price of the cryptocurrencies from the Coinmarketcap API
        """
        logger.debug("Get current maket prices form Coinmarketcap for:\n%s", tokens)

        names = str(",").join(tokens)
        logger.info("Request tokens current prices for %s", names)
        if debug:
            logger.info(
                "Debug mode: use sandbox-api.coinmarketcap.com instead of pro-api.coinmarketcap.com"
            )
            url = (
                "https://sandbox-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"
            )
            # In debug mode, use the sandbox API with the provided token
            # Sandbox API keys should be configured in settings
            headers = {"X-CMC_PRO_API_KEY": str(self.coinmarketcap_token)}
        else:
            url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"
            headers = {"X-CMC_PRO_API_KEY": str(self.coinmarketcap_token)}

        params = {
            "symbol": names,
            "convert": unit,
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            logger.info("Get current market prices from Coinmarketcap successfully")
            content = response.json()
            crypto_prices = {}
            for name in content["data"]:
                # Initialiser l'entrée pour chaque token
                crypto_prices[name] = {"price": 0, "unit": unit}
                try:
                    price_data = content["data"][name][0]["quote"][unit]["price"]
                    if price_data is not None:
                        crypto_prices[name]["price"] = price_data
                    logger.debug("Price for %s: %s", name, price_data)
                except (KeyError, IndexError, TypeError) as e:
                    logger.error("Error getting price for %s : %s", name, str(e))
                    logger.debug("Data received: %s", content["data"][name])
            return crypto_prices
        else:
            logger.error("API request failed with status code: %d", response.status_code)
            logger.debug("Error response: %s", response.text)
            return None
