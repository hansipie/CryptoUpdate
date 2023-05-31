# notion-crypto-integration

Integrate auto cryptocurrencies price update to Notion.

## Install the required software dependencies by running the following command,
    
    python3 -m pip install -r requirements.txt

## create ./inputs/my_variables.yml file with your notion and coinmarketcap related informations,
    
    DATABASE_ID: <insert-your-notion-database-id>
    NOTION_VERSION: <insert-API-notion-version>
    MY_NOTION_SECRET_TOKEN: <insert-your-notion-integration-secret-token> 
    MY_NOTION_INTERNAL_TOKEN: <insert-your-notion-integration-internal-token>
    MY_NOTION_FILE_TOKEN: <insert-your-notion-file-token>
    MY_COINMARKETCAP_APIKEY: <insert-your-coinmarketcap-integration-secret-token>

## Run the following command to execute python script,
    
    python3 main.py
    
    This command will update the notion Dashboard with coins current values and save it in the archives directory as a CSV file.
    
## Archives processing

    python processArchive.py
    
    This command will process the archives directory to create a CSV file for wallets evolution throught time.
    
