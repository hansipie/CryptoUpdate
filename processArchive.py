#%% import libs
import os
import mydata
import pandas as pd

#%% dataframe initialisation
df = pd.DataFrame({})

#%% make archive path
archivepath = os.path.join(os.getcwd(), "archives")
dirs = os.listdir(archivepath)

#%% crawl in archive dirs
for d in dirs:
    if not d.isnumeric():
        continue
    print("directory: ", d)
    sub = os.path.join(archivepath, d)
    files = os.listdir(sub)
    for f in files:
        fullf = os.path.join(sub, f)
        print("file: ", fullf)
        dico = mydata.ExtractData(fullf)
        newdf = pd.DataFrame([dico])
        df = pd.concat([df,newdf])
        print("------------------")

#%% sort dataframe by date
df.set_index("Timestamp",inplace=True)
df.sort_index(inplace=True)


#%% add sum column
all_sum = df.sum(axis=1, numeric_only=True)
df["_Sum"] = all_sum

#%% print description
print(df.describe())
print("------------------")

#%% create final file
outputfile = os.path.join(os.getcwd(), "./outputs/ArchiveFinal.csv")
print("Write ", outputfile)
os.remove(outputfile)
df.to_csv(outputfile)