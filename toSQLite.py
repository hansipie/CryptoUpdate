import os
import csv
import sqlite3
import pandas as pd

def get_headers(repertoire_csv):
    headers = []
    for mon_dossier in os.listdir(repertoire_csv):
        chemin_dossier_csv = os.path.join(repertoire_csv, mon_dossier)
        for nom_fichier in os.listdir(chemin_dossier_csv):
            if nom_fichier.endswith(".csv"):
                chemin_fichier = os.path.join(chemin_dossier_csv, nom_fichier)
                print("fichier : %s" % chemin_fichier)            
                # Extraction des données du fichier CSV
                with open(chemin_fichier, "r") as fichier_csv:
                    lecteur_csv = csv.reader(fichier_csv)
                    for ligne in lecteur_csv:
                        headers += ligne
                        break
    unique_headers = list(set(headers))
    print("unique headers : %s" % unique_headers)
    return unique_headers

# Chemin vers le répertoire contenant les fichiers CSV
repertoire_csv = "./archives/"

headers_table = get_headers(repertoire_csv)

# Connexion à la base de données SQLite
conn = sqlite3.connect("./outputs/archives.db")
c = conn.cursor()

# Création des tables "Repertoire" et "Fichier_CSV" dans la base de données
c.execute("""CREATE TABLE IF NOT EXISTS Repertoire (
                id INTEGER PRIMARY KEY,
                temps_epoch INTEGER
            )""")

c.execute("""CREATE TABLE IF NOT EXISTS Fichier_CSV (
                id INTEGER PRIMARY KEY,
                id_repertoire INTEGER,
                relation_achats TEXT,
                nom TEXT,
                chaine TEXT,
                montant_investi REAL,
                coin_investi TEXT,
                prix_coin REAL,
                coins_wallet REAL,
                valeur_wallet REAL,
                nfts INTEGER,
                valeur_nfts REAL,
                valeur_totale REAL,
                benefice_net REAL,
                prix_coin_investi REAL,
                relation_nfts TEXT,
                relation_wallets TEXT,
                url_notion TEXT,
                FOREIGN KEY (id_repertoire) REFERENCES Repertoire(id)
            )""")

# Parcours des fichiers CSV dans le répertoire
for mon_dossier in os.listdir(repertoire_csv):
    chemin_dossier_csv = os.path.join(repertoire_csv, mon_dossier)
    temps_epoch = int(os.path.splitext(mon_dossier)[0])
    
    # Insertion des données dans la base de données
    c.execute("""INSERT INTO Repertoire (temps_epoch)
                VALUES (?)""", (temps_epoch,))
    id_repertoire = c.lastrowid

    for nom_fichier in os.listdir(chemin_dossier_csv):
        if nom_fichier.endswith(".csv"):
            chemin_fichier = os.path.join(chemin_dossier_csv, nom_fichier)
            print("fichier : %s" % chemin_fichier)            
            # Extraction des données du fichier CSV
            with open(chemin_fichier, "r") as fichier_csv:
                df = pd.read_csv(fichier_csv)
                df.to_sql('tmp_table', conn, if_exists='replace')
                c.execute('''ALTER TABLE tmp_table ADD COLUMN id_repertoire INTEGER''')
                c.execute('''UPDATE tmp_table SET id_repertoire = ?''', (id_repertoire,))

                # lecteur_csv = csv.reader(fichier_csv)
                # next(lecteur_csv)
                # print('---------------------------------------')
                # for ligne in lecteur_csv:
                #     if (len(ligne) != 16):
                #         print ('-----> /!\ bypass')
                #         continue
                #     print('ligne : ', ligne)
                #     relation_achats = ligne[0]
                #     nom = ligne[1]
                #     chaine = ligne[2]
                #     montant_investi = float(ligne[3]) if ligne[3] else 0.0
                #     coin_investi = ligne[4]
                #     prix_coin = float(ligne[5]) if ligne[5] else 0.0
                #     coins_wallet = float(ligne[6]) if ligne[6] else 0.0
                #     valeur_wallet = float(ligne[7]) if ligne[7] else 0.0
                #     nfts = float(ligne[8]) if ligne[8] else 0.0
                #     valeur_nfts = float(ligne[9]) if ligne[9] else 0.0
                #     valeur_totale = float(ligne[10]) if ligne[10] else 0.0
                #     benefice_net = float(ligne[11]) if ligne[11] else 0.0
                #     prix_coin_investi = float(ligne[12]) if ligne[12] else 0.0
                #     relation_nfts = ligne[13]
                #     relation_wallets = ligne[14]
                #     url_notion = ligne[15]
                    
                #     # Insertion des données dans la base de données
                #     c.execute("""INSERT INTO Fichier_CSV (id_repertoire, relation_achats, nom, chaine, montant_investi,
                #                                         coin_investi, prix_coin, coins_wallet, valeur_wallet, nfts,
                #                                         valeur_nfts, valeur_totale, benefice_net, prix_coin_investi,
                #                                         relation_nfts, relation_wallets, url_notion)
                #                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                #             (id_repertoire, relation_achats, nom, chaine, montant_investi, coin_investi, prix_coin,
                #             coins_wallet, valeur_wallet, nfts, valeur_nfts, valeur_totale,
                #             benefice_net, prix_coin_investi, relation_nfts, relation_wallets, url_notion))

# Validation et sauvegarde des modifications dans la base de données
conn.commit()

# Fermeture de la connexion à la base de données
conn.close()
