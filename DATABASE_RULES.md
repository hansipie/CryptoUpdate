# Règles de validation de la base de données

## Table: Operations

### Opérations avec source = 0 (AIRDROPS)

**IMPORTANT: Les opérations avec `source = 0` sont VALIDES**

Ces opérations représentent des **airdrops de tokens** où des tokens sont reçus gratuitement sans coût monétaire.

**Exemples d'airdrops dans la base:**
- ID 295: KYROS airdrop (104.72 tokens reçus)
- ID 297: 0G airdrop (139.49 tokens reçus)
- ID 298: BORG airdrop (2.89 tokens reçus)
- ID 300: BORG airdrop (2.82 tokens reçus)

**Structure d'un airdrop:**
```
type: "buy"
source: 0.0 (pas de coût)
destination: [montant de tokens reçus]
source_unit: "EUR" (ou autre devise)
destination_unit: [symbole du token]
```

⚠️ **Ne jamais supprimer ou considérer comme invalides ces opérations!**

---

## Table: TokenMetadata

### Tokens délistés

Les tokens suivants sont **délistés** et ne sont plus tradés:

| Token | Date de délisting | Dernier prix valide | Notes |
|-------|-------------------|---------------------|-------|
| **KYROS** | 2025-10-14 | N/A | Jamais eu de prix valide |
| **ANV** | 2024-05-13 | 2024-05-13 | 96.5% des prix à 0 |
| **ANC** | 2025-07-22 | 2025-06-12 | Prix à 0 depuis juillet 2025 |
| **FXS** | 2025-05-09 | 2025-04-30 | 12% des prix à 0 |
| **MATIC** | 2025-04-09 | 2025-03-21 | Migré vers POL |

### Tokens actifs avec erreurs API historiques

Ces tokens sont **actifs** mais ont quelques enregistrements de prix à 0 dus à des erreurs API:

| Token | Enregistrements à 0 | Status |
|-------|---------------------|--------|
| **SEN** | 187 | ✅ Actif |
| **MXNA** | 23 | ✅ Actif |
| **D2T** | 23 | ✅ Actif |
| **LUNA** | 6 (crash mai 2022) | ✅ Actif (LUNA 2.0) |
| **TITA** | 2 | ✅ Actif |

### Utilisation de TokenMetadata

```python
from modules.token_metadata import TokenMetadataManager, TokenStatus

manager = TokenMetadataManager(db_path="data/db.sqlite3")

# Vérifier si un token est actif
if manager.is_token_active('BTC'):
    print("Token actif, peut être utilisé")

# Vérifier si un token est délisté
if manager.is_token_delisted('MATIC'):
    print("Token délisté, ne pas afficher dans l'UI principale")

# Filtrer une liste de tokens
active_tokens = manager.filter_active_tokens(['BTC', 'ETH', 'MATIC', 'KYROS'])
# Retourne: ['BTC', 'ETH'] (MATIC et KYROS sont délistés)

# Récupérer les infos complètes
info = manager.get_token_info('MATIC')
print(f"Status: {info['status']}")
print(f"Notes: {info['notes']}")
```

---

## Nettoyage effectué

### ✅ Corrections appliquées

1. **Schéma Operations**: Correction de `INTEGERT` → `INTEGER`
2. **Foreign Key Portfolios_Tokens**: Correction de la référence vers `Portfolios(id)`
3. **Références orphelines**: Suppression de 2 enregistrements (portfolio_id 411)
4. **Prix invalides pour tokens délistés**:
   - Supprimés 646 enregistrements avec prix = 0 pour tokens délistés dans Market
   - Supprimés 287 enregistrements avec prix = 0 pour tokens délistés dans TokensDatabase

### 📊 Statistiques après nettoyage

| Table | Enregistrements avant | Enregistrements après | Supprimés |
|-------|----------------------|----------------------|-----------|
| **Market** | 92,102 | 91,456 | 646 |
| **TokensDatabase** | 71,270 | 70,983 | 287 |
| **Portfolios_Tokens** | 47 | 45 | 2 |

### ⚠️ Données préservées

- **253 enregistrements** avec prix = 0 pour tokens actifs (erreurs API historiques) - CONSERVÉS
- **4 opérations** avec source = 0 (airdrops) - CONSERVÉS comme VALIDES

---

## Sauvegardes

Une sauvegarde de la base de données a été créée avant toute modification:
- `data/db.sqlite3.backup` - Sauvegarde complète avant corrections

---

## Scripts SQL disponibles

- `fix_schema.sql` - Correction du schéma (déjà appliqué)
- `add_token_metadata.sql` - Création de la table TokenMetadata (déjà appliqué)

---

## Recommandations pour le développement futur

1. **Filtrer les tokens délistés dans l'UI**: Utiliser `TokenMetadataManager.is_token_active()` avant d'afficher les tokens
2. **Identifier les airdrops**: Les opérations avec `source = 0` et `type = 'buy'` sont des airdrops
3. **Gestion des erreurs API**: Les prix à 0 pour tokens actifs peuvent indiquer des problèmes d'API - logger ces erreurs
4. **Maintenance**: Vérifier régulièrement les nouveaux tokens pour ajouter leurs métadonnées si nécessaire

---

---

## Migrations de schéma

| Version | Description |
|---------|-------------|
| v1 | Création de toutes les tables de base |
| v2 | `TokenMetadata`: ajout colonnes `mr_id`, `name` |
| v3 | `TokenMetadata`: renommage `mr_id` → `mraccoon_id` |
| v4 | `TokenMetadata`: ajout `id AUTOINCREMENT`, `token` n'est plus PK |
| v5 | `Swaps`: ajout colonne `note TEXT` |
| v6 | `TokenMetadata`: ajout colonne `mraccoon_id` unique index |
| v7 | `Swaps`: conversion `amount_from`/`amount_to` de TEXT en REAL |

*Dernière mise à jour: 2026-04-18*
