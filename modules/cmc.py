from datetime import datetime
import logging
import pytz
import requests

logger = logging.getLogger(__name__)


class cmc:
    def __init__(self, coinmarketcap_token: str) -> dict:
        self.coinmarketcap_token = coinmarketcap_token
        pass

    def getCurrentFiatPrices(
        self, converts: list = ["USD"], symbol="EUR", amount=1, debug=False
    ) -> dict:
        """
        Get the price of the fiat currencies from the Coinmarketcap API
        """
        logger.debug(f"Get current maket prices form Coinmarketcap for:\n{converts}")
        names = str(",").join(converts)
        logger.info(f"Request fiat current prices for {names}")
        if debug:
            logger.info(
                "Debug mode: use sandbox-api.coinmarketcap.com instead of pro-api.coinmarketcap.com"
            )
            url = "https://sandbox-api.coinmarketcap.com/v2/tools/price-conversion"
            headers = {"X-CMC_PRO_API_KEY": "b54bcf4d-1bca-4e8e-9a24-22ff2c3d462c"}
        else:
            url = "https://pro-api.coinmarketcap.com/v2/tools/price-conversion"
            headers = {"X-CMC_PRO_API_KEY": str(self.coinmarketcap_token)}

        params = {
            "amount": amount,
            "symbol": symbol,
            "convert": names,
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            fiat_prices = {}
            content = response.json()
            logger.info(
                f"Get current market prices from Coinmarketcap successfully\n{content}"
            )
            for fiat in converts:
                # Initialiser l'entrée pour chaque token
                fiat_prices[fiat] = {"price": 0, "timestamp": 0}
                try:
                    logger.debug(
                        f"Price for {fiat}: {content["data"][0]["quote"][fiat]}"
                    )
                    price_data = content["data"][0]["quote"][fiat]["price"]
                    timestamp_data = content["data"][0]["quote"][fiat]["last_updated"]

                    if price_data is not None:
                        fiat_prices[fiat]["price"] = price_data
                        utc_time = datetime.strptime(timestamp_data, "%Y-%m-%dT%H:%M:%S.%fZ")
                        fiat_prices[fiat]["timestamp"] = utc_time.replace(tzinfo=pytz.UTC).timestamp()
                        
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"Error getting price for {fiat}: {str(e)}")
                    logger.error(f"Data received: {content["data"]}")
                    continue
            return fiat_prices
        else:
            logger.error(f"Error: {response.status_code}")
            logger.error(response.text)
            return None

    def getCryptoPrices(self, tokens: list, unit="EUR", debug=False):
        """
        Get the price of the cryptocurrencies from the Coinmarketcap API
        """
        logger.debug(f"Get current maket prices form Coinmarketcap for:\n{tokens}")

        names = str(",").join(tokens)
        logger.info(f"Request tokens current prices for {names}")
        if debug:
            logger.info(
                "Debug mode: use sandbox-api.coinmarketcap.com instead of pro-api.coinmarketcap.com"
            )
            url = (
                "https://sandbox-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"
            )
            headers = {"X-CMC_PRO_API_KEY": "b54bcf4d-1bca-4e8e-9a24-22ff2c3d462c"}
        else:
            url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"
            headers = {"X-CMC_PRO_API_KEY": str(self.coinmarketcap_token)}

        params = {
            "symbol": names,
            "convert": unit,
        }

        response = requests.get(url, headers=headers, params=params)
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
                    logger.debug(f"Price for {name}: {crypto_prices[name]['price']}")
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"Error getting price for {name}: {str(e)}")
                    logger.debug(f"Data received: {content['data'][name]}")
            return crypto_prices
        else:
            logger.error(f"Error: {response.status_code}")
            logger.error(response.text)
            return None
