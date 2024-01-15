import math
import os
import time
import csv
from modules import Notion

class Exporter:

    def __init__(self, notion_apikey):
        self.notion = Notion.Notion(notion_apikey)

    def GetCSVfile(self, database_name):
        """Get the dashboard data from notion and save it to a csv file"""
        epochstr = str(math.floor(time.time()))
        destpath = os.path.join(os.getcwd(), "archives", epochstr, "archive.csv")

        dashboard_id = self.notion.getObjectId(database_name, "database")
        if dashboard_id is None:
            print("Error: Dashboard database not found")
            return None
        entities = self.notion.getNotionDatabaseEntities(dashboard_id)
        dashboard = self.notion.getEntitiesFromDashboard(entities)

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
