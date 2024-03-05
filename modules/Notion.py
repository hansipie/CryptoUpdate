import time
import traceback
import requests
import logging
from alive_progress import alive_bar

class Notion:
    def __init__(self, apikey, version="2022-06-28"):
        self.apikey = apikey
        self.version = version
        self.base_url = "https://api.notion.com"

    def getObjectId(self, name, type, parent=None):
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
                "Price/Coin (€)": {
                    "name": "Price/Coin (€)",
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
                        "expression": 'multiply(prop("Price/Coin (€)"), prop("Coins in wallet"))'
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
            logging.info(f"Get page {page_id} successfully.")
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
            logging.error(f"Error getting page. code: {response.status_code}")
            return None
        
    def getNotionFormlaValue(self, page_id, formula_id):
        url = f"{self.base_url}/v1/pages/{page_id}/properties/{formula_id}"
        headers = {
            "Notion-Version": str(self.version),
            "Authorization": "Bearer " + str(self.apikey),
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            logging.info(f"Get formula value in page {page_id} successfully.")
            return response.json()["formula"]["number"]
        else:
            logging.error(
                f"Error getting formula value in page {page_id}. code: {response.status_code}"
            )
            return None

    def getEntitiesFromDashboard(self, entities) -> dict:
        ret = {}
        with alive_bar(
            len(entities),
            title="Get market prices",
            force_tty=True,
            stats="(eta:{eta})",
        ) as bar:
            for entry in entities:
                properties = entry["properties"]
                try:
                    token = properties["Token"]["title"][0]["text"]["content"]
                except:
                    logging.error(f"Invalid token entry in Dashboard: {entry["id"]}")
                    continue
                if properties["Price/Coin (€)"]["number"] is None:
                    price = 0
                else:
                    price = float(properties["Price/Coin (€)"]["number"])
                
                logging.debug(f"Coins in wallet: {properties["Coins in wallet"]}")
                if properties["Coins in wallet"]["type"] == "number":
                    count = float(properties["Coins in wallet"]["number"])
                elif properties["Coins in wallet"]["type"] == "rollup":
                    count = float(properties["Coins in wallet"]["rollup"]["number"])
                else:
                    count = -1

                logging.debug(f"Token: {token}, Price: {price}, Count: {count}")
                ret[token] = {}
                ret[token]["Price/Coin (€)"] = price
                ret[token]["Coins in wallet"] = count
                bar()
        return ret

    def getEntitiesFromAssets(self, entities) -> dict:
        sum_formula_id = None
        ret = {}
        with alive_bar(
            len(entities), title="Get token counts", force_tty=True, stats="(eta:{eta})"
        ) as bar:
            for entry in entities:
                properties = entry["properties"]
                try:
                    token = properties["Token"]["title"][0]["text"]["content"]
                except:
                    logging.error(f"Invalid token entry in Assets: {entry["id"]}")
                    continue

                if sum_formula_id is None:
                    sum_formula_id = properties["Sum"]["id"]
                sum = self.getNotionFormlaValue(entry["id"], sum_formula_id)

                logging.debug(f"Token: {token}, Sum: {sum}")
                ret[token] = {}
                ret[token]["sum"] = sum
                bar()
        return ret
