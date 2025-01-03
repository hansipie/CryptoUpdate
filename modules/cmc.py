import logging
import requests

logger = logging.getLogger(__name__)


class cmc:
    def __init__(self, coinmarketcap_token: str) -> dict:
        self.coinmarketcap_token = coinmarketcap_token
        pass

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
            crypto_prices = {}
            content = response.json()
            logger.info("Get current market prices from Coinmarketcap successfully")
            for name in content["data"]:
                # Initialiser l'entrée pour chaque token
                crypto_prices[name] = {"price": 0}
                try:
                    price_data = content["data"][name][0]["quote"][unit]["price"]
                    if price_data is not None:
                        crypto_prices[name]["price"] = price_data
                    logger.debug(f"Price for {name}: {crypto_prices[name]['price']}")
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"Error getting price for {name}: {str(e)}")
                    logger.error(f"Data received: {content['data'][name]}")
            logger.debug(f"Final prices: {crypto_prices}")
            return crypto_prices
        else:
            logger.error(f"Error: {response.status_code}")
            logger.error(response.text)
            return None
