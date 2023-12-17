import requests
from alive_progress import alive_bar

class Notion:
    def __init__(self, apikey, version="2022-06-28"):
        self.apikey = apikey
        self.version = version
        self.base_url = "https://api.notion.com"

    def getDatabaseId(self, name):
        """
        Get the database ID of the Notion database
        """
        url = f"{self.base_url}/v1/search"
        headers = {
            'Notion-Version': str(self.version),
            'Authorization': 'Bearer ' + str(self.apikey)
        }
        body = {"query": name}
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 200:
            print(f"Get database {name} id successfully: {response.json()['results'][0]['id']}")
            return response.json()["results"][0]["id"]
        else:
            print("Error getting database id. code:", response.status_code)
            quit()

    def getNotionDatabaseEntities(self, database_id):
        """
        Get all the Notion database entities and their properties
        """
        url = f"{self.base_url}/v1/databases/{database_id}/query"
        headers = {
            'Notion-Version': str(self.version),
            'Authorization': 'Bearer ' + str(self.apikey)
        }
        response = requests.post(url, headers=headers)
        resp = response.json()
        print(f"Get database entities successfully. Total: {len(resp['results'])}")
        return resp["results"]
    
    def getNotionPage(self, page_id):
        """
        Get all the Notion database entities and their properties
        """
        url = f"{self.base_url}/v1/pages/{page_id}"
        headers = {
            'Notion-Version': str(self.version),
            'Authorization': 'Bearer ' + str(self.apikey)
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error getting page {page_id}. code:", response.status_code)
            return None
        else:
            resp = response.json()
            return resp
        
    def patchNotionPage(self, page_id, properties):
        """
        Patch a Notion page with new properties
        """
        url = f"{self.base_url}/v1/pages/{page_id}"
        headers = {
            'Notion-Version': str(self.version),
            'Authorization': 'Bearer ' + str(self.apikey),
            'Content-Type': 'application/json'
        }

        response = requests.patch(url, headers=headers, data=properties)
        if response.status_code != 200:
            print(f"Error patching page {page_id}. code:", response.status_code, response.text)
            return None
        else:
            resp = response.json()
            return resp
    
    def getNotionFormlaValue(self, page_id, formula_id):
        url = f"{self.base_url}/v1/pages/{page_id}/properties/{formula_id}"
        headers = {
            'Notion-Version': str(self.version),
            'Authorization': 'Bearer ' + str(self.apikey)    
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error getting formula value in page {page_id}. code:", response.status_code)
            return None
        else:
            resp = response.json()
            return resp["formula"]["number"]
        
    def getEntitiesFromDashboard(self, entities) -> dict:
        ret = {}
        with alive_bar(len(entities), title='Get market prices', force_tty=True, stats='(eta:{eta})') as bar:
            for entry in entities:
                properties = entry["properties"]
                try:
                    token = properties["Token"]["title"][0]["text"]["content"]
                except:
                    print("Invalid token entry in Dashboard: ", entry["id"])
                    continue
                if properties["Price/Coin"]["number"] is None:
                    price = 0
                else:
                    price = float(properties["Price/Coin"]["number"])

                #print(f"Token: {token}, Price: {price}")
                ret[token] = {}
                ret[token]["Price/Coin"] = price
                bar()
        return ret

    def getEntitiesFromAssets(self, entities) -> dict:
        sum_formula_id = None
        ret = {}
        with alive_bar(len(entities), title='Get token counts', force_tty=True, stats='(eta:{eta})') as bar:
            for entry in entities:
                properties = entry["properties"]
                try:
                    token = properties["Token"]["title"][0]["text"]["content"]
                except:
                    print("Invalid token entry in Assets: ", entry["id"])
                    continue

                if sum_formula_id is None:
                    sum_formula_id = properties["Sum"]["id"]
                sum= self.getNotionFormlaValue(entry["id"], sum_formula_id)

                #print(f"Token: {token}, Sum: {sum}")
                ret[token] = {}
                ret[token]["sum"] = sum
                bar()
        return ret
