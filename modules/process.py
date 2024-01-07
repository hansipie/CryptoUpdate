import pandas as pd

def dropDuplicate(conn):
    try:
        df = pd.read_sql_query("SELECT * from Database;", conn)
    except:
        print("Database is empty. Skipping...")
        return 
    dupcount = df.duplicated().sum()
    print(f"Found {len(df)} rows with {dupcount} duplicated rows")
    if dupcount > 0:
        print(f"Found {dupcount} duplicated rows. Dropping...") 
        df.drop_duplicates(inplace=True)
        df.to_sql('Database', conn, if_exists='replace', index=False)

def getDateFrame(inputfile, epoch):
    print(f"Reading {inputfile}")
    df = pd.read_csv(inputfile)
    df.fillna(0, inplace=True)
    dftemp = df[["Token","Price/Coin","Coins in wallet"]]
    dftemp.columns = ["token","price","count"]
    dfret = dftemp.copy()
    dfret['timestamp'] = epoch
    print(f"Found {len(dfret)} rows")
    return dfret