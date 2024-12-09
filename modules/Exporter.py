import math
import os
import time
import csv
import logging
from modules import Notion

class Exporter:

    def __init__(self, notion_apikey, archive_path):
        self.notion = Notion.Notion(notion_apikey)
        self.epochstr = str(math.floor(time.time()))
        self.archive_path = archive_path

    def __getDashboardData(self, database_name):
        """Get the dashboard data from notion"""
        dashboard_id = self.notion.getObjectId(database_name, "database")
        if dashboard_id is None:
            logging.debug(f"Error: {database_name} database not found")
            return None
        entities = self.notion.getNotionDatabaseEntities(dashboard_id)
        if entities is None:
            logging.warning(f"Warning: {database_name} database is empty")
            return None
        dashboard = self.notion.getEntitiesFromDashboard(entities)
        return dashboard

    def GetCSVfile(self, database_name):
        
        destpath = os.path.join(self.archive_path, f"{self.epochstr}.csv")
        dashboard = self.__getDashboardData(database_name)

        #save dict to csv file
        if not os.path.exists(os.path.dirname(destpath)):
            os.makedirs(os.path.dirname(destpath))
        with open(destpath, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Token", "Market Price", "Coins in wallet", "Timestamp"])
            for token in dashboard:
                writer.writerow([token, dashboard[token]["Market Price"], dashboard[token]["Coins in wallet"], self.epochstr])

        return(destpath)

if __name__ == "__main__":
    destpath = Exporter().GetCSVfile()
    logging.info(f"output cvs file: {destpath}")
