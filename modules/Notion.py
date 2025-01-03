import time
import traceback
import requests
import logging
from alive_progress import alive_bar

class Notion:
    def __init__(self, apikey: str, version: str = "2022-06-28"):
        self.apikey = apikey
        self.version = version
        self.base_url = "https://api.notion.com"

    def getObjectId(self, name: str, type: str, parent: str = None) -> str | None:
        """
        Get the database/page ID of the Notion object
        """
        url = f"{self.base_url}/v1/search"
        headers = {
            "Notion-Version": str(self.version),
            "Authorization": "Bearer " + str(self.apikey),
        }
        body = {"query": name, "filter": {"value": type, "property": "object"}}
        logging.info(f"Get {type} {name} id... {body}")

        count = 0
        while True:
            response = requests.post(url, headers=headers, json=body)
            if response.status_code == 200:
                try:
                    result_id = None
                    results = response.json()["results"]
                    for result in results:
                        #check Object type
                        if result["object"] == "database":
                            if result["title"][0]["text"]["content"] != name:
                                continue;
                        elif result["object"] == "page":
                            if "title" not in result["properties"] or result["properties"]["title"]["title"][0]["text"]["content"] != name:
                                continue;
                        else:
                            continue

                        if parent is not None:
                            if result["parent"]["type"] == "page_id":
                                #check parent page
                                parent_json = self.getNotionPage(result["parent"]["page_id"])
                                if parent_json["properties"]["title"]["title"][0]["text"]["content"] == parent:
                                    result_id = result["id"]
                            else:
                                continue
                        else:
                            result_id = result["id"]
                            break
                    logging.debug(f"Returned {type} {name} id: {result_id}")
                    return result_id
                except:
                    traceback.print_exc()   
                    logging.error(f"Error getting {type} {name} id.")
                    return None
            else:
                logging.error(f"Error getting {type} {name} id. code: {response.status_code}")
                count += 1
                if count > 5:
                    logging.warning("Max retry reached. Exit.")
                    return None
                time.sleep(1)
                logging.warning(f"Retry getting {type} id. code:{response.status_code}")

    def createDatabase(self, name, parent):
        """
        Create a Notion database
        """

        page_id = self.getObjectId(parent, "page")
        if page_id is None:
            logging.error("Error: Parent page not found")
            return None
        
        db_id = self.getObjectId(name, "database", parent)
        if db_id is not None:
            logging.error("Error: Database already exists")
            return "DB_EXISTS"

        url = f"{self.base_url}/v1/databases"
        headers = {
            "Notion-Version": str(self.version),
            "Authorization": "Bearer " + str(self.apikey),
        }
        body = {
            "parent": {"type": "page_id", "page_id": page_id},
            "title": [
                {"type": "text", "text": {"content": name, "link": None}}
            ],
            "properties": {
                "Token": {"id": "title", "name": "Token", "type": "title", "title": {}},
                "Market Price": {
                    "name": "Market Price",
                    "type": "number",
                    "number": {"format": "number"},
                },
                "Coins in wallet": {
                    "name": "Coins in wallet",
                    "type": "number",
                    "number": {"format": "number"},
                },
                "Wallet Value (€)": {
                    "name": "Wallet Value (€)",
                    "type": "formula",
                    "formula": {
                        "expression": 'multiply(prop("Market Price"), prop("Coins in wallet"))'
                    },
                },
            },
        }

        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 200:
            logging.debug(f"Create database {name} successfully.")
            return response.json()["id"]
        else:
            logging.error(f"Error creating database {name}. code: {response.status_code}")
            return None

    def getNotionDatabaseEntities(self, database_id):
        """
        Get all the Notion database entities and their properties
        """
        url = f"{self.base_url}/v1/databases/{database_id}/query"
        headers = {
            "Notion-Version": str(self.version),
            "Authorization": "Bearer " + str(self.apikey),
        }

        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            logging.info(
                f"Get database entities successfully. Total: {len(response.json()['results'])}"
            )
            return response.json()["results"]
        else:
            logging.error(f"Error getting database entities. code: {response.status_code}")
            return None

    def getNotionPage(self, page_id):
        """
        Get a Notion page and its properties
        """
        url = f"{self.base_url}/v1/pages/{page_id}"
        headers = {
            "Notion-Version": str(self.version),
            "Authorization": "Bearer " + str(self.apikey),
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            logging.debug(f"Get page {page_id} successfully.")
            return response.json()
        else:
            logging.error("Error getting page. code: {response.status_code}")
            return None


    def patchNotionPage(self, page_id, properties):
        """
        Patch a Notion page with new properties
        """
        url = f"{self.base_url}/v1/pages/{page_id}"
        headers = {
            "Notion-Version": str(self.version),
            "Authorization": "Bearer " + str(self.apikey),
            "Content-Type": "application/json",
        }

        response = requests.patch(url, headers=headers, data=properties)
        if response.status_code == 200:
            logging.debug(f"Patch page {page_id} successfully.")
            return response.json()
        else:
            logging.error(f"Error patching page. code: {response.status_code}")
            return None
        
    def getNotionPageProperties(self, page_id : str, property_id : str) -> dict:
        url = f"{self.base_url}/v1/pages/{page_id}/properties/{property_id}"
        headers = {
            "Notion-Version": str(self.version),
            "Authorization": "Bearer " + str(self.apikey),
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logging.error(
                f"Error getting formula value in page {page_id}. code: {response.status_code}"
            )
            return None
        logging.debug(f"Page {page_id} type: {response.json()["type"]}")
        return response.json()

    def getSumFromAsset(self, page_id : str) -> float:
        logging.debug(f"Get Sum from asset page {page_id}")
        page_json = self.getNotionPage(page_id)
        for key in page_json["properties"]:
            if key == "Sum":
                sum_formula_value = page_json["properties"][key]["formula"]["number"]
                logging.debug(f"Sum formula value: {sum_formula_value}")
                return sum_formula_value

    def getEntitiesFromDashboard(self, entities) -> dict:
        ret = {}
        with alive_bar(
            len(entities),
            title="Get Dashboard Entities",
            force_tty=True,
            stats="(eta:{eta})",
        ) as bar:
            for entry in entities:
                properties = entry["properties"]

                # token
                try:
                    token = properties["Token"]["title"][0]["text"]["content"]
                except:
                    logging.warning(f"Invalid token entry in Dashboard: {entry["id"]}")
                    continue

                # price
                if properties["Market Price"]["number"] is None:
                    price = 0
                else:
                    price = float(properties["Market Price"]["number"])
                
                # coins in wallet
                logging.debug(f"Coins in wallet type: {properties["Coins in wallet"]["type"]}")
                if properties["Coins in wallet"]["type"] == "number":
                    count = float(properties["Coins in wallet"]["number"])
                elif properties["Coins in wallet"]["type"] == "rollup":
                    page_json = self.getNotionPageProperties(entry["id"], properties["Coins in wallet"]["id"])
                    if page_json == None:
                        logging.warning(f"Invalid property id {properties["Coins in wallet"]["id"]}")
                        continue
                    if page_json["type"] == "property_item":
                        logging.debug(f"Property results: {page_json["results"]}")
                        if not page_json["results"]:
                            logging.debug(f"Property 'results' is empty for {token}")
                            count = 0
                        elif page_json["results"][0]["type"] == "relation":
                            asset_pageid = page_json["results"][0]["relation"]["id"]
                            count = self.getSumFromAsset(asset_pageid)
                        elif page_json["results"][0]["type"] == "formula":
                            count = page_json["results"][0]["formula"]["number"]
                        else:
                            logging.warning(f"Invalid property results type {page_json["results"][0]["type"]}. Type expected : relation or formula")
                            continue
                    else:
                        logging.warning(f"Invalid property type {page_json["type"]}. Type expected : property_item")
                        continue
                else:
                    count = -1

                logging.debug(f"Token: {token}, Market Price: {price}, Coins in wallet: {count}")
                ret[token] = {}
                ret[token]["Market Price"] = price
                ret[token]["Coins in wallet"] = count
                bar()
        return ret
