import tempfile
import logging
import csv
import os
from .models import CsvStore

logger = logging.getLogger(__name__)

# Dictionnaire de mappage des noms de colonnes CSV aux noms de champs du modèle
CSV_FIELD_MAPPING = {
    "Token": "token",
    "Amount Invested (€)": "amount_invested",
    "Coins Invested": "coins_invested",
    "Coin Invested": "coins_invested",  # Ajoutez une autre clé pour gérer les fautes de frappe
    "Price/Coin": "coin_price",
    "Coins in wallet": "coins_count",
    "Wallet Value (€)": "wallet_value",
    "NFTs": "nfts_count",
    "NFTs Value (€)": "nfts_value",
    "Total Value (€)": "total_value",
    "Net Profit (€)": "profit",
    "Timestamp": "timestamp",
}

def handle_uploaded_file(f):
    logger.debug(f"Uploading file {f}")
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        for chunk in f.chunks():
            temp_file.write(chunk)
        temp_file_path = temp_file.name
    logger.debug(f"Fichier temporaire créé à : {temp_file_path}")

    # Ajouter le code pour lire le fichier CSV et enregistrer les données dans la base de données
    # Utiliser la fonction csv.DictReader pour lire le fichier CSV
    with open(temp_file_path, mode="r", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Transformer les noms des colonnes du CSV en noms de champs du modèle
            transformed_row = {
                CSV_FIELD_MAPPING.get(k, k): (0 if not v else v)
                for k, v in row.items()
                if k in CSV_FIELD_MAPPING
            }
            # Utiliser le modèle Django pour enregistrer les données dans la base de données
            logger.debug(f"Ligne transformée et enregistrée : {transformed_row}")
            CsvStore.objects.create(**transformed_row)
            

    # Supprimer le fichier temporaire
    os.remove(temp_file_path)

