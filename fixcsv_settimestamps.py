import os
import csv
import typer
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fixcsv(directory):
    for timestamp in os.listdir(directory):
        logger.info(f"Processing directory: {timestamp}")
        if os.path.isdir(os.path.join(directory, timestamp)):
            for filename in os.listdir(os.path.join(directory, timestamp)):
                if filename.endswith(".csv"):
                    filepath = os.path.join(directory, timestamp, filename)
                    # open file and add a new column to the CSV file with the name "Timestamp" and the value of the current timestamp
                    with open(filepath, mode="r", encoding="utf-8-sig") as csvfile:
                        reader = csv.reader(csvfile)
                        rows = list(reader)
                    #check if row timsstamp already exists
                    if "Timestamp" in rows[0]:
                        logger.info(f"Timestamp already exists in file: {filepath}")
                        continue
                    # else add timestamp to the first row and the value to the rest of the rows
                    with open(filepath, mode="w", encoding="utf-8-sig", newline="") as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(rows[0] + ["Timestamp"])
                        for row in rows[1:]:
                            writer.writerow(row + [timestamp])
                    logger.info(f"Added timestamp to file: {filepath}")
 
if __name__ == "__main__":
    typer.run(fixcsv)