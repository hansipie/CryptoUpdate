import json
import time
import requests
import os
from alive_progress import alive_bar
from dotenv import load_dotenv
from modules import Notion

class Updater:

    def __init__(self):
        self.notion_entries = {}
        self.notion = Notion.Notion(os.getenv('NOTION_API_TOKEN'))
        self.database_id = self.notion.getDatabaseId("Dashboard")
        self.lastupdate_id = self.notion.getDatabaseId("LastUpdate")
        self.notion_entries = self.getNotionDatabaseEntries()

    def getNotionDatabaseEntries(self):
        resp = {}
        for v in self.notion.getNotionDatabaseEntities(self.database_id):
            try:
                text = v["properties"]["Token"]["title"][0]["text"]["content"]
            except:
                print("Invalid entry in Dashboard: ", v["id"])
                continue
            if v["properties"]["Price/Coin"]["number"] is None:
                price = 0
            else:
                price = float(v["properties"]["Price/Coin"]["number"])
            resp.update({
                text: {
                    "page": v["id"], 
                    "price": price
                    }
                })
        return resp

    def getCryptoPrices(self):
        """
        Get the price of the cryptocurrencies from the Coinmarketcap API
        """
        names = ""
        for name in self.notion_entries:
            if len(names) > 0:
               names += ","
            names += name                        
        print('Request tokens current prices for', names)   
        url = 'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest'
        #url = 'https://sandbox-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest'
        params = {
            'symbol': names,
            'convert':'EUR',
        }
        headers = {
                'X-CMC_PRO_API_KEY': os.getenv('MY_COINMARKETCAP_APIKEY'),
                #'X-CMC_PRO_API_KEY': 'b54bcf4d-1bca-4e8e-9a24-22ff2c3d462c',
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            content = response.json()
            print("Get current maket prices form Coinmarketcap successfully")
            for name in content['data']:
                try:
                    if content['data'][name][0]['quote']['EUR']['price'] is None:
                        self.notion_entries[name]['price'] = 0
                    else:
                        self.notion_entries[name]['price'] = content['data'][name][0]['quote']['EUR']['price']
                except:
                    print("Error getting current coins values (",name,"). Set to null.")
                    self.notion_entries[name]['price'] = 0
        else:
            print("Error getting current coins values. code: ", response.status_code)
            quit()

    def UpdateDBHandleError(self, response):
        print("Error updating Notion database. code: ", response.status_code)
        if response.status_code == 429:
            print(" - Rate limit exceeded. Retry after ", retry_after, " seconds")
            retry_after = int(response.headers['Retry-After'])
        elif response.status_code == 522:
            print(" - Connection timed out. Retry.")
            retry_after = 2
        else:
            print(" - Unknown error updating Notion database. Quit.")
            quit()
        time.sleep(retry_after)

    def UpdateLastUpdate(self):
        """
        Update the Notion database with the current time
        """

        resp = self.notion.getNotionDatabaseEntities(self.lastupdate_id)
        pageId = resp[0]["id"]

        properties = json.dumps({
            "properties": {
                "date": {
                    "type": "date",
                    "date": {
                        "start": str(time.strftime("%Y-%m-%d %H:%M:%S"))
                    }
                }
            }
        })
        self.notion.patchNotionPage(pageId, properties)

    def updateNotionDatabase(self, pageId, coinPrice):
        """
        A notion database (if integration is enabled) page with id `pageId`
        will be updated with the data `coinPrice`.
        """
        properties = json.dumps({
            "properties": {
                "Price/Coin": {
                    "type": "number",
                    "number": float(coinPrice)
                }
            }
        })
        self.notion.patchNotionPage(pageId, properties)


    def UpdateCrypto(self):
        """
        Update the Notion database with the current price of the cryptocurrency
        """
        self.getCryptoPrices()

        count=len(self.notion_entries)
        with alive_bar(count, title='Updating Notion database', force_tty=True, stats='(eta:{eta})') as bar:
            for _, data in self.notion_entries.items():
                self.updateNotionDatabase(
                    pageId=data['page'],
                    coinPrice=data['price']
                )
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
                print(f"[Error encountered]: {e}")
                break


if __name__ == "__main__":
    # With 😴 sleeps to prevent rate limit from kicking in.
    Updater().UpdateIndefinitely()
