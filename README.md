# **Crypto Update**

Integrate auto cryptocurrencies price update to Notion and archive database.

## **Install the required software dependencies by running the following command**
    
    python3 -m pip install -r requirements.txt

## **Create ./inputs/my_variables.yml file with your notion and coinmarketcap related informations**
    
    DATABASE_ID: <insert-your-notion-database-id>
    NOTION_VERSION: <insert-API-notion-version>
    NOTION_API_TOKEN: <insert-your-notion-integration-secret-token> 
    NOTION_TOKEN_V2: <insert-your-notion-integration-internal-token>
    NOTION_FILE_TOKEN: <insert-your-notion-file-token>
    MY_COINMARKETCAP_APIKEY: <insert-your-coinmarketcap-integration-secret-token>

### **How to find those values**

NOTION_API_TOKEN: It has to be created from your Notion account (https://www.notion.so/my-integrations)

NOTION_VERSION: It is found in the API documentation (https://developers.notion.com/reference/versioning)

DATABASE_ID:

NOTION_TOKEN_V2:

NOTION_FILE_TOKEN:

MY_COINMARKETCAP_APIKEY: It is found in your API account (https://pro.coinmarketcap.com/account)

## **Notion's database structure**

This is the general structure of the database processed:

```json
{
	"object": "database",
	"title": [
		{
			"type": "text",
			"text": {
				"content": "Dashboard",
			},
			"plain_text": "Dashboard",
		}
	],
	"properties": {
		"Name": {
			"id": "title",
			"name": "Name",
			"type": "title",
			"title": {}
		},
		"Price/Coin": {
			"name": "Price/Coin",
			"type": "number",
			"number": {
				"format": "number"
			}
		},
		"Coins in wallet": {
			"name": "Coins in wallet",
			"type": "number",
			"number": {
				"format": "number"
			}
		},
		"Wallet Value (€)": {
			"name": "Wallet Value (€)",
			"type": "formula",
			"formula": {
				"expression": "multiply(prop(\"Price/Coin\"), prop(\"Coins in wallet\"))"
			}
		}
	}
}
```
## **Run the following command to execute python script**
    
    python3 main.py
    
This command will update the notion Dashboard with coins current values and save it in the archives directory as a CSV file.
    
## **Archives processing**

    python processArchive.py
    
This command will process the archives directory to create a CSV file for wallets evolution throught time.
    
## **Credits**

- https://github.com/tnvmadhav/notion-crypto-integration (update notion database)
- https://github.com/yannbolliger/notion-exporter (donwload database to a CSV file)