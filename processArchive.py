import os
import mydata
import pandas as pd
import matplotlib.pyplot as plt

df = pd.DataFrame({})

archivepath = os.path.join(os.getcwd(), "archives")
dirs = os.listdir(archivepath)
for d in dirs:
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

df.set_index("Timestamp",inplace=True)
df.sort_index(inplace=True)

all_sum = df.sum(axis=1, numeric_only=True)
df["_Sum"] = all_sum
print(df.describe())
print("------------------")

outputfile = os.path.join(os.getcwd(), "./outputs/ArchiveFinal.csv")
print("Write ", outputfile)
os.remove(outputfile)
df.to_csv(outputfile)