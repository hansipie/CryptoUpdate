import json
import time
import traceback
import requests
import logging
from alive_progress import alive_bar
from dotenv import load_dotenv
from modules import Notion, cmc

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
            if v["properties"]["Market Price"]["number"] is None:
                price = 0
            else:
                price = float(v["properties"]["Market Price"]["number"])
            resp.update({text: {"page": v["id"], "price": price}})
        return resp

    def getCryptoPrices(self):
        """
        Get the price of the cryptocurrencies from the Coinmarketcap API
        """
        cmc_prices = cmc.cmc(self.coinmarketcap_token)
        upd_table = cmc_prices.getCryptoPrices(self.notion_entries)
        if upd_table is not None:
            self.notion_entries = upd_table
        else:
            logging.error("Error getting current coins values. Quit.")
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
                    "Market Price": {"type": "number", "number": float(coinPrice)},
                }
            }
        )
        self.notion.patchNotionPage(pageId, properties)

    def UpdateCrypto(self):
        """
        Update the Notion database with the current price of the cryptocurrency
        """
        self.getCryptoPrices()

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
