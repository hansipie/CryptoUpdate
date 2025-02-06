import json
import time
import traceback
import logging
from alive_progress import alive_bar
from modules import Notion
from modules.database.market import Market

logger = logging.getLogger(__name__)
class Updater:
    def __init__(
        self, dbfile: str, coinmarketcap_token: str, notion_token: str, notion_dbid: str
    ):
        self.notion_entries = {}
        self.dbfile = dbfile
        self.notion = Notion.Notion(notion_token)
        self.coinmarketcap_token = coinmarketcap_token
        self.notion_dbid = notion_dbid
        self.lastupdate_id = self.notion.getObjectId("LastUpdate", "database")
        self.notion_entries = self.getNotionDatabaseEntries()

    def getNotionDatabaseEntries(self):
        resp = {}
        for v in self.notion.getNotionDatabaseEntities(self.notion_dbid):
            try:
                text = v["properties"]["Token"]["title"][0]["text"]["content"]
            except KeyError:
                logger.error("Invalid entry in Dashboard: %s", v["id"])
                continue
            logger.debug("Found entry: %s", text)
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
        tokens = list(self.notion_entries.keys())
        market = Market(self.dbfile, self.coinmarketcap_token)
        market.update_market(tokens)
        market.update_currencies()
        tokens_prices = market.getLastMarket()
        if tokens_prices is None:
            logger.error("No Market data available")
            return
        
        for token in tokens:
            if token not in tokens_prices:
                logger.debug(f"Token {token} not found in market data")
                continue
            logger.debug(f"Updating {token} with price {tokens_prices[token]} in Notion database")
            self.notion_entries[token]["price"] = tokens_prices[token]
  

    def UpdateDBHandleError(self, response):
        logger.error("Error updating Notion database. code: %d", response.status_code)
        if response.status_code == 429:
            retry_after = int(response.headers["Retry-After"])
            logger.warning(
                " - Rate limit exceeded. Retry after %d seconds" , retry_after
            )
        elif response.status_code == 522:
            logger.warning(" - Connection timed out. Retry.")
            retry_after = 2
        else:
            logger.error(" - Unknown error updating Notion database. Quit.")
            quit()
        time.sleep(retry_after)

    def UpdateLastUpdate(self):
        """
        Update the Notion database with the current time
        """

        if self.lastupdate_id is None:
            logger.warning("Warning: LastUpdate database not found")
        else:
            logger.info("Updating last update...")
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
            except Exception:
                traceback.print_exc()
                break


if __name__ == "__main__":
    # With 😴 sleeps to prevent rate limit from kicking in.
    Updater().UpdateIndefinitely()
