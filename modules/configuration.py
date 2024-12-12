import configparser
import logging
import os

logger = logging.getLogger(__name__)

class configuration:

    def __init__(self, inifile: str = "./settings.ini"):
        logger.debug("Loading configuration")
        self.inifile = inifile
        self.conf = None

    def readConfig(self):
        if not os.path.exists(self.inifile):
            logger.error("Settings file not found: " + self.inifile)
            raise FileNotFoundError
        self.conf = configparser.ConfigParser()
        self.conf.read(self.inifile)

    def saveConfig(self, settings: dict):
        logger.debug("Saving configuration")
        if self.conf is None:
            try:
                self.readConfig()
            except FileNotFoundError:
                self.conf = configparser.ConfigParser()
        try:
            self.conf["Notion"] = {
                "token": settings["notion_token"],
                "database": settings["notion_database"],
                "parentpage": settings["notion_parentpage"],
            }
            self.conf["Coinmarketcap"] = {
                "token": settings["coinmarketcap_token"],
            }
            self.conf["OpenAI"] = {
                "token": settings["openai_token"],
            }
            self.conf["Debug"] = {
                "flag": str(settings["debug_flag"]),
            }

            with open(self.inifile, "w") as configfile:
                self.conf.write(configfile)
        except Exception as e:
            logger.error("Error: " + type(e).__name__ + " - " + str(e))
            quit()
