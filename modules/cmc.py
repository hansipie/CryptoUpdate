import logging
import requests

logger = logging.getLogger(__name__)


class cmc:
    def __init__(self, coinmarketcap_token: str) -> dict:
        self.coinmarketcap_token = coinmarketcap_token
        pass

    def getCryptoPrices(self, tokens: dict, unit="EUR", debug=False):
        """
        Get the price of the cryptocurrencies from the Coinmarketcap API
        """
        logger.debug(f"Get current maket prices form Coinmarketcap for:\n{tokens}")
        names = str(",").join(tokens.keys())
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
            content = response.json()
            logger.info("Get current maket prices form Coinmarketcap successfully")
            for name in content["data"]:
                try:
                    if content["data"][name][0]["quote"][unit]["price"] is None:
                        tokens[name]["price"] = 0
                    else:
                        tokens[name]["price"] = content["data"][name][0]["quote"][unit][
                            "price"
                        ]
                except:
                    logger.error(f"Error: {content['data'][name][0]}")
                    tokens[name]["price"] = 0
            logger.debug(f"Prices: {tokens}")
            return tokens
        else:
            logger.error(f"Error: {response.status_code}")
            logger.error(response.text)
            return None
