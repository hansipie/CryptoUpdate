import json
import time
import traceback
import requests
import logging
from alive_progress import alive_bar
from dotenv import load_dotenv
from modules import Notion

class Updater:
    def __init__(self, coinmarketcap_token: str, notion_token: str, database_id: str):
        self.notion_entries = {}
        self.notion = Notion.Notion(notion_token)
        self.coinmarketcap_token = coinmarketcap_token
        self.database_id = database_id
        self.lastupdate_id = self.notion.getObjectId("LastUpdate", "database")
        self.notion_entries = self.getNotionDatabaseEntries()

    def getNotionDatabaseEntries(self):
        resp = {}
        for v in self.notion.getNotionDatabaseEntities(self.database_id):
            try:
                text = v["properties"]["Token"]["title"][0]["text"]["content"]
            except:
                logging.error("Invalid entry in Dashboard: ", v["id"])
                continue
            logging.debug(f"Found entry: {text}")
            if v["properties"]["Price/Coin"]["number"] is None:
                price = 0
            else:
                price = float(v["properties"]["Price/Coin"]["number"])
            resp.update({text: {"page": v["id"], "price": price}})
        return resp

    def getCryptoPrices(self, debug=False):
        """
        Get the price of the cryptocurrencies from the Coinmarketcap API
        """
        # names = ""
        # for name in self.notion_entries:
        #     if len(names) > 0:
        #         names += ","
        #     names += name
        names = str(",").join(self.notion_entries)
        ##
        logging.info(f"Request tokens current prices for {names}")
        if debug:
            logging.debug(
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
            "convert": "EUR",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            content = response.json()
            logging.info("Get current maket prices form Coinmarketcap successfully")
            for name in content["data"]:
                try:
                    if content["data"][name][0]["quote"]["EUR"]["price"] is None:
                        self.notion_entries[name]["price"] = 0
                    else:
                        self.notion_entries[name]["price"] = content["data"][name][0][
                            "quote"
                        ]["EUR"]["price"]
                except:
                    logging.error(
                        "Error getting current coins values (", name, "). Set to null."
                    )
                    self.notion_entries[name]["price"] = 0
        else:
            logging.error(f"Error getting current coins values. code: {response.status_code}")
            quit()

    def UpdateDBHandleError(self, response):
        logging.error("Error updating Notion database. code: ", response.status_code)
        if response.status_code == 429:
            logging.warning(" - Rate limit exceeded. Retry after ", retry_after, " seconds")
            retry_after = int(response.headers["Retry-After"])
        elif response.status_code == 522:
            logging.warning(" - Connection timed out. Retry.")
            retry_after = 2
        else:
            logging.error(" - Unknown error updating Notion database. Quit.")
            quit()
        time.sleep(retry_after)

    def UpdateLastUpdate(self):
        """
        Update the Notion database with the current time
        """

        if self.lastupdate_id is None:
            logging.warning("Warning: LastUpdate database not found")
        else:
            logging.info("Updating last update...")
            resp = self.notion.getNotionDatabaseEntities(self.lastupdate_id)
            pageId = resp[0]["id"]

            properties = json.dumps(
                {
                    "properties": {
                        "date": {
                            "type": "date",
                            "date": {"start": str(time.strftime("%Y-%m-%d %H:%M:%S"))},
                        }
                    }
                }
            )
            self.notion.patchNotionPage(pageId, properties)

    def updateNotionDatabase(self, pageId, coinPrice):
        """
        A notion database (if integration is enabled) page with id `pageId`
        will be updated with the data `coinPrice`.
        """
        properties = json.dumps(
            {
                "properties": {
                    "Price/Coin": {"type": "number", "number": float(coinPrice)}
                }
            }
        )
        self.notion.patchNotionPage(pageId, properties)

    def UpdateCrypto(self, debug=False):
        """
        Update the Notion database with the current price of the cryptocurrency
        """
        self.getCryptoPrices(debug=debug)

        count = len(self.notion_entries)
        with alive_bar(
            count, title="Updating Notion database", force_tty=True, stats="(eta:{eta})"
        ) as bar:
            for _, data in self.notion_entries.items():
                self.updateNotionDatabase(pageId=data["page"], coinPrice=data["price"])
                bar()
        self.UpdateLastUpdate()

    def UpdateIndefinitely(self):
        """
        Orchestrates downloading prices and updating the same
        in notion database.
        """
        while True:
            try:
                self.UpdateCrypto()
                time.sleep(1 * 60)
            except Exception as e:
                traceback.print_exc()
                break


if __name__ == "__main__":
    # With 😴 sleeps to prevent rate limit from kicking in.
    Updater().UpdateIndefinitely()
