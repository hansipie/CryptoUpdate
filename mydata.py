import pandas as pd
import time
import os

def ExtractData(file):
    df = pd.DataFrame({})
    df = pd.read_csv(file)

    dico = {}
    epoch = int(os.path.basename(os.path.dirname(file)))
    epochformat = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch))
    dico['Timestamp'] = epochformat
    for _,row in df.iterrows() :
        dico[row['Name']] = row['Wallet Value (€)']
    print("New data :")
    print(dico)
    return dico

def makeDataFrame(path):
    """
    Read all CSV files in a directory and concatenate them into a single DataFrame
    
    :param path: The path to the folder containing the CSV files
    :return: A dataframe with the sum of all the columns.
    """
    all = pd.DataFrame({})
    files=os.listdir(path)
    for f in files:
        fullpath = os.path.join(path, f)
        print("Read CSV file: ", fullpath)
        if all.empty:
            all = pd.read_csv(fullpath, index_col="Timestamp")
            continue
        df = pd.read_csv(fullpath, index_col="Timestamp")
        all = pd.concat([all,df])
    all = all.sort_index().reindex(sorted(all.columns), axis=1)
    print(all)
    return all
    