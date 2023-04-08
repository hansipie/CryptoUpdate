import math
import os
import shutil
import tempfile
import time
import zipfile
import requests
import json
import yaml

class Exporter:

    def __init__(self):
        with open("./inputs/my_variables.yml", 'r') as stream:
            try:
                self.my_variables_map = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print("[Error]: while reading yml file", exc)
        self.my_variables_map["TASK_ID"]=self.EnqueueTask()

    def EnqueueTask(self):
        url = "https://www.notion.so/api/v3/enqueueTask"
        payload = json.dumps({
            "task": {
                "eventName": "exportBlock",
                "request": {
                    "block": {
                        "id": self.my_variables_map["DATABASE_ID"]
                    },
                    "recursive": False,
                    "exportOptions": {
                        "exportType": "markdown",
                        "timeZone": "Europe/Paris",
                        "locale": "en"
                    }
                }
            }
        })
        headers = {
        'Cookie': 'token_v2=' + self.my_variables_map["MY_NOTION_INTERNAL_TOKEN"],
        'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        print(response);
        resp = response.json()
        return(resp["taskId"])

    def GetTasks(self):
        url = "https://www.notion.so/api/v3/getTasks"
        payload = json.dumps({
        "taskIds": [
            self.my_variables_map["TASK_ID"]
        ]
        })
        headers = {
        'Cookie': 'token_v2=' + self.my_variables_map["MY_NOTION_INTERNAL_TOKEN"],
        'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        return(response.json())

    def DownloadArchive(self, url, dest):
        print("Download url: " + url)
        headers = {'Cookie': 'file_token=' + self.my_variables_map["MY_NOTION_FILE_TOKEN"]}
        response = requests.request("GET", url, headers=headers)
        if (response.status_code != 200):
            print("Error downloading archive (code:", response.status_code, ")")
            quit()
        destfile = os.path.join(dest,"archive.zip")
        with open(destfile, "wb") as f:
            f.write(response.content)
        print("File downloaded: ", destfile)
        return(destfile)

    def GetCSVfile(self):
        epochstr = str(math.floor(time.time()))
        destpath = os.path.join(os.getcwd(), "archives", epochstr)
        temppath = tempfile.mkdtemp()
        loop = 1
        while (loop == 1):
            resp = self.GetTasks()
            for v in resp["results"]:
                print("state: " + v["state"])
                if (v["state"] == "success"):
                    if (v["status"]["type"] == "complete"):
                        print("status: " + v["status"]["type"])
                        archive = self.DownloadArchive(v["status"]["exportURL"], temppath)
                        with zipfile.ZipFile(archive, 'r') as zip_ref:
                            zip_ref.extractall(destpath)
                        loop = 0
                        break
                print("retry")
        shutil.rmtree(temppath)
        return(destpath)

if __name__ == "__main__":
    destpath = Exporter().GetCSVfile()
    print("output directory: ", destpath)
