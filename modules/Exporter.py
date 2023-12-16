import math
import os
import time
import csv
from modules import Notion

class Exporter:

    def __init__(self):
        self.notion = Notion.Notion(os.getenv('NOTION_API_TOKEN'))

    def GetCSVfile(self):
        epochstr = str(math.floor(time.time()))
        destpath = os.path.join(os.getcwd(), "archives", epochstr, "archive.csv")

        assets_id = self.notion.getDatabaseId("Assets")
        entities = self.notion.getNotionDatabaseEntities(assets_id)
        assets = self.notion.getEntitiesFromAssets(entities)

        dashboard_id = self.notion.getDatabaseId("Dashboard")
        entities = self.notion.getNotionDatabaseEntities(dashboard_id)
        dashboard = self.notion.getEntitiesFromDashboard(entities)

        #merge assets and dashboard
        for token in dashboard:
            if token in assets:
                dashboard[token]["Coins in wallet"] = assets[token]["sum"]
            else:
                dashboard[token]["Coins in wallet"] = 0

        #save dict to csv file

        if not os.path.exists(os.path.dirname(destpath)):
            os.makedirs(os.path.dirname(destpath))

        with open(destpath, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Token", "Price/Coin", "Coins in wallet"])
            for token in dashboard:
                writer.writerow([token, dashboard[token]["Price/Coin"], dashboard[token]["Coins in wallet"]])

        return(destpath)

if __name__ == "__main__":
    destpath = Exporter().GetCSVfile()
    print("output cvs file: ", destpath)
