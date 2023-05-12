import os
import sys
import shutil
from datetime import datetime, timedelta

def get_epoch_folder_date(folder_name):
    try:
        return datetime.fromtimestamp(int(folder_name)).date()
    except (ValueError, OSError): 
        return None

def get_folder_names_by_date(folder_path):
    folders = os.listdir(folder_path)
    folders_by_date = {}
    for folder in folders:
        epoch_folder_date = get_epoch_folder_date(folder)
        if epoch_folder_date is None:
            continue
        if epoch_folder_date not in folders_by_date:
            folders_by_date[epoch_folder_date] = []
        folders_by_date[epoch_folder_date].append(folder)
    return folders_by_date

def keep_first_and_last_folders(folder_names):
    folder_dates = sorted([get_epoch_folder_date(name) for name in folder_names])
    return [folder_names[0], folder_names[-1]]

def keep_folders_by_date(folder_path):
    folders_by_date = get_folder_names_by_date(folder_path)
    folders_to_keep = []
    for folder_date, folder_names in folders_by_date.items():
        folders_to_keep += keep_first_and_last_folders(folder_names)
    folders_to_rename = [folder for folder in os.listdir(folder_path) if folder not in folders_to_keep]
    for folder in folders_to_rename:
        folder_path_to_rename = os.path.join(folder_path, folder)
        newname = os.path.join(folder_path, "todelete_" + folder)
        if os.path.isdir(folder_path_to_rename):
            print(f"Renaming folder {folder_path_to_rename} (", get_epoch_folder_date(folder), ") to ", newname)
            try:
                os.rename(folder_path_to_rename, newname)
                print(f"Renamed successfully")
            except OSError as e:
                print(f"Rename error: {e}")
        else:
            print(f"Directory {folder_path_to_rename} is not a directory")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py folder_path")
        sys.exit(1)
    folder_path = sys.argv[1]
    keep_folders_by_date(folder_path)
