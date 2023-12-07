#%% import libs
import os
import time
import pandas as pd
from alive_progress import alive_bar

def ExtractData(file):
    df = pd.DataFrame({})
    df = pd.read_csv(file)

    dico = {}
    epoch = int(os.path.basename(os.path.dirname(file)))
    epochformat = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch))
    dico['Timestamp'] = epochformat
    for _,row in df.iterrows() :
        if type(row['Tokens']) == str:
            dico[row['Tokens']] = row['Wallet Value (€)']
    return dico

#%% dataframe initialisation
df = pd.DataFrame({})

#%% make archive path
archivepath = os.path.join(os.getcwd(), "archives")
dirs = os.listdir(archivepath)

#%% crawl in archive dirs
count = len(dirs)
with alive_bar(count, title='Extracting data', force_tty=True, stats='(eta:{eta})') as bar:
    for d in dirs:
        if not d.isnumeric():
            continue
        sub = os.path.join(archivepath, d)
        files = os.listdir(sub)
        count=len(files)
        for f in files:
            if f.endswith("_all.csv"):
                continue
            fullf = os.path.join(sub, f)
            dico = ExtractData(fullf)
            newdf = pd.DataFrame([dico])
            df = pd.concat([df,newdf])
        bar()

#%% sort dataframe by date
df.set_index("Timestamp",inplace=True)
df.sort_index(inplace=True)

## set all nan to 0
df.fillna(0, inplace=True)

#%% add sum column
all_sum = df.sum(axis=1, numeric_only=True)
df["_Sum"] = all_sum

#%% print description
print(df.describe())
print("------------------")

#%% create final file
outputfile = os.path.join(os.getcwd(), "outputs")
outputfile = os.path.join(outputfile, "ArchiveFinal.csv")
print("Write ", outputfile)
os.remove(outputfile)
df.to_csv(outputfile)