import json
import time
import requests
import yaml
from alive_progress import alive_bar

class Updater:

    def __init__(self):
        """
        Reads the my_variables.yml file and gets the notion_database_id and the notion_entries
        """
        """
        Gets required variable data from config yaml file.
        """
        with open("./inputs/my_variables.yml", 'r') as stream:
            try:
                self.my_variables_map = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print("[Error]: while reading yml file", exc)
        self.my_variables_map["NOTION_ENTRIES"] = {}
        self.getDatabaseId()
        self.getNotionDatabaseEntities()

    def getDatabaseId(self):
        """
        Get the database ID of the Notion database
        """
        url = "https://api.notion.com/v1/search"
        headers = {
            'Notion-Version': str(self.my_variables_map["NOTION_VERSION"]),
            'Authorization':
                'Bearer ' + self.my_variables_map["NOTION_API_TOKEN"]
        }
        body = {'filter': {'value': 'database','property': 'object'}}
        response = requests.post(url, headers=headers, json=body)
        self.my_variables_map["DATABASE_ID"] = response.json()["results"][0]["id"]

    def getNotionDatabaseEntities(self):
        """
        Get all the Notion database entities and their properties
        """
        url = f"https://api.notion.com/v1/databases/{self.my_variables_map['DATABASE_ID']}/query"
        headers = {
            'Notion-Version': str(self.my_variables_map["NOTION_VERSION"]),
            'Authorization': 'Bearer ' + self.my_variables_map["NOTION_API_TOKEN"]
        }
        response = requests.post(url, headers=headers)
        resp = response.json()
        for v in resp["results"]:
            text = v["properties"]["Name"]["title"][0]["text"]["content"]
            if v["properties"]["Price/Coin"]["number"] is None:
                price = 0
            else:
                price = float(v["properties"]["Price/Coin"]["number"])
            self.my_variables_map["NOTION_ENTRIES"].update({
                v["properties"]["Name"]["title"][0]["text"]["content"]: {
                    "page": v["id"], 
                    "price": price
                    }
                })

    def getCryptoPrices(self):
        """
        Get the price of the cryptocurrencies from the Coinmarketcap API
        """
        names = ""
        for name in self.my_variables_map["NOTION_ENTRIES"]:
            if len(names) > 0:
               names += ","
            names += name                        
        print('Request tokens current prices for ', names)   
        url = 'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest'
        #url = 'https://sandbox-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest'
        params = {
            'symbol': names,
            'convert':'EUR',
        }
        headers = {
                'X-CMC_PRO_API_KEY': self.my_variables_map["MY_COINMARKETCAP_APIKEY"],
                #'X-CMC_PRO_API_KEY': 'b54bcf4d-1bca-4e8e-9a24-22ff2c3d462c',
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            content = response.json()
            print("Get current coins value successfully")
            for name in content['data']:
                self.my_variables_map["NOTION_ENTRIES"][name]['price'] = content['data'][name][0]['quote']['EUR']['price']
        else:
            print("Error getting current coins values. code: ", response.status_code)
            quit()

    def updateNotionDatabase(self, pageId, coinPrice):
        """
        A notion database (if integration is enabled) page with id `pageId`
        will be updated with the data `coinPrice`.
        """
        url = "https://api.notion.com/v1/pages/" + str(pageId)
        headers = {
            'Authorization':
                'Bearer ' + self.my_variables_map["NOTION_API_TOKEN"],
            'Notion-Version': str(self.my_variables_map["NOTION_VERSION"]),
            'Content-Type': 'application/json'
        }
        payload = json.dumps({
            "properties": {
                "Price/Coin": {
                    "type": "number",
                    "number": float(coinPrice)
                }
            }
        })
        requests.request("PATCH", url, headers=headers, data=payload)

    def UpdateCrypto(self):
        """
        Update the Notion database with the current price of the cryptocurrency
        """
        self.getCryptoPrices()

        count=len(self.my_variables_map["NOTION_ENTRIES"])
        with alive_bar(count, title='Updating Notion database', force_tty=True, stats='(eta:{eta})') as bar:
            for _, data in self.my_variables_map["NOTION_ENTRIES"].items():
                self.updateNotionDatabase(
                    pageId=data['page'],
                    coinPrice=data['price']
                )
                time.sleep(5)
                bar()

    def UpdateCryptoSilent(self):
        """
        Update the Notion database with the current price of the cryptocurrency
        ... without display
        """
        self.getCryptoPrices()
        
        print('Updating Notion ...')
        for _, data in self.my_variables_map["NOTION_ENTRIES"].items():
            self.updateNotionDatabase(
                pageId=data['page'],
                coinPrice=data['price']        
            )
            time.sleep(5)

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
