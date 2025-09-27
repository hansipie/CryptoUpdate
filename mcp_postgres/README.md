# MCP PostgreSQL Server Docker Setup

Configuration Docker complète pour le serveur MCP PostgreSQL avec base de données, interface d'administration et cache Redis.

## Structure du Projet

```
mcp_postgres/
├── Dockerfile                 # Image MCP PostgreSQL server
├── docker-compose.yml         # Orchestration complète
├── init/                      # Scripts d'initialisation DB
│   ├── 01-init-database.sql   # Structure de base
│   └── 02-migrate-from-sqlite.sql # Migration SQLite → PostgreSQL
├── pgadmin/                   # Configuration pgAdmin
│   └── servers.json           # Serveurs pré-configurés
├── backups/                   # Répertoire des sauvegardes
├── logs/                      # Logs du serveur MCP
└── README.md                  # Cette documentation
```

## Démarrage Rapide

### 1. Lancement des Services

```bash
cd mcp_postgres

# Démarrer tous les services
docker-compose up -d

# Vérifier le statut
docker-compose ps

# Suivre les logs
docker-compose logs -f mcp-postgres-server
```

### 2. Accès aux Services

- **PostgreSQL**: `localhost:5432`
  - Database: `cryptoupdate`
  - User: `crypto_user`
  - Password: `crypto_password`

- **MCP Server**: `localhost:3000`

- **pgAdmin**: `http://localhost:8080`
  - Email: `admin@crypto.local`
  - Password: `admin`

- **Redis**: `localhost:6379`

## Configuration

### Variables d'Environnement

```bash
# Base de données
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=cryptoupdate
POSTGRES_USER=crypto_user
POSTGRES_PASSWORD=crypto_password

# Serveur MCP
LOG_LEVEL=INFO
PYTHONPATH=/app

# pgAdmin
PGADMIN_DEFAULT_EMAIL=admin@crypto.local
PGADMIN_DEFAULT_PASSWORD=admin
```

### Ports Exposés

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5432 | Base de données |
| MCP Server | 3000 | Serveur MCP |
| pgAdmin | 8080 | Interface web admin |
| Redis | 6379 | Cache (optionnel) |

## Migration depuis SQLite

### 1. Export des Données SQLite

```bash
# Se connecter à la base SQLite existante
sqlite3 data/db.sqlite3

# Exporter chaque table
.mode csv
.header on
.output portfolios.csv
SELECT * FROM portfolios;

.output transactions.csv
SELECT * FROM operations;

# Répéter pour toutes les tables
```

### 2. Import dans PostgreSQL

```bash
# Se connecter au container PostgreSQL
docker exec -it crypto-postgres psql -U crypto_user -d cryptoupdate

# Importer les données
\COPY portfolio.portfolios(name, description, created_at) FROM '/backups/portfolios.csv' WITH (FORMAT csv, HEADER true);

# Mettre à jour les holdings
SELECT update_portfolio_holdings();
```

### 3. Validation de la Migration

```sql
-- Vérifier les comptes de records
SELECT * FROM migration.validation_summary;

-- Comparer avec SQLite
-- sqlite3 data/db.sqlite3 "SELECT COUNT(*) FROM portfolios;"
```

## Gestion de la Base de Données

### Connexion Directe

```bash
# Connexion via psql
docker exec -it crypto-postgres psql -U crypto_user -d cryptoupdate

# Connexion via pgAdmin
# Ouvrir http://localhost:8080
# Les serveurs sont pré-configurés
```

### Commandes Utiles

```sql
-- Lister les schémas
\dn

-- Lister les tables par schéma
\dt crypto.*
\dt portfolio.*
\dt market.*
\dt operations.*

-- Voir la structure d'une table
\d portfolio.portfolios

-- Vérifier les index
\di
```

## Sauvegarde et Restauration

### Sauvegarde Automatique

```bash
# Créer une sauvegarde
docker exec crypto-postgres pg_dump -U crypto_user -d cryptoupdate > mcp_postgres/backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Sauvegarde avec compression
docker exec crypto-postgres pg_dump -U crypto_user -d cryptoupdate | gzip > mcp_postgres/backups/backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Script de Sauvegarde

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/cryptoupdate_$TIMESTAMP.sql.gz"

docker exec crypto-postgres pg_dump -U crypto_user -d cryptoupdate | gzip > "$BACKUP_FILE"
echo "Backup created: $BACKUP_FILE"

# Garder seulement les 7 dernières sauvegardes
ls -t $BACKUP_DIR/cryptoupdate_*.sql.gz | tail -n +8 | xargs rm -f
```

### Restauration

```bash
# Restaurer depuis une sauvegarde
gunzip -c mcp_postgres/backups/backup_20241227_143022.sql.gz | docker exec -i crypto-postgres psql -U crypto_user -d cryptoupdate

# Ou sans compression
docker exec -i crypto-postgres psql -U crypto_user -d cryptoupdate < mcp_postgres/backups/backup_20241227_143022.sql
```

## Développement

### Mode Développement

```bash
# Arrêter le serveur MCP pour développement local
docker-compose stop mcp-postgres-server

# Garder seulement PostgreSQL et pgAdmin
docker-compose up -d postgres pgadmin redis

# Développer localement avec accès à la DB
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=cryptoupdate
export POSTGRES_USER=crypto_user
export POSTGRES_PASSWORD=crypto_password

uv run python your_mcp_server.py
```

### Debugging

```bash
# Logs détaillés
docker-compose logs -f --tail=100 mcp-postgres-server

# Accéder au container MCP
docker exec -it crypto-mcp-postgres bash

# Tester la connexion PostgreSQL
docker exec crypto-postgres pg_isready -U crypto_user -d cryptoupdate

# Monitor les connexions
docker exec -it crypto-postgres psql -U crypto_user -d cryptoupdate -c "SELECT * FROM pg_stat_activity;"
```

## Performance et Monitoring

### Optimisation PostgreSQL

```sql
-- Vérifier les statistiques des tables
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del 
FROM pg_stat_user_tables;

-- Analyser les requêtes lentes
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Mettre à jour les statistiques
ANALYZE;
```

### Configuration Avancée

```yaml
# docker-compose.yml - Section PostgreSQL
postgres:
  image: postgres:16-alpine
  command: [
    "postgres",
    "-c", "shared_preload_libraries=pg_stat_statements",
    "-c", "pg_stat_statements.track=all",
    "-c", "log_statement=all",
    "-c", "log_min_duration_statement=1000",
    "-c", "max_connections=200",
    "-c", "shared_buffers=256MB",
    "-c", "effective_cache_size=1GB"
  ]
```

## Sécurité

### Recommandations Production

1. **Changer les mots de passe par défaut**
2. **Utiliser SSL/TLS**
3. **Configurer les règles de firewall**
4. **Limiter les connexions réseau**
5. **Chiffrer les sauvegardes**

### Configuration SSL

```bash
# Générer des certificats SSL
openssl req -new -x509 -days 365 -nodes -text -out server.crt -keyout server.key -subj "/CN=postgres"

# Monter dans le container
volumes:
  - ./ssl/server.crt:/var/lib/postgresql/server.crt:ro
  - ./ssl/server.key:/var/lib/postgresql/server.key:ro
```

## Troubleshooting

### Problèmes Courants

1. **Connexion refusée**
   ```bash
   # Vérifier que PostgreSQL est démarré
   docker-compose ps postgres
   
   # Vérifier les logs
   docker-compose logs postgres
   ```

2. **Erreur de permissions**
   ```bash
   # Réinitialiser les permissions
   docker exec crypto-postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE cryptoupdate TO crypto_user;"
   ```

3. **Espace disque insuffisant**
   ```bash
   # Nettoyer les volumes non utilisés
   docker volume prune
   
   # Vérifier l'espace utilisé
   docker system df
   ```

### Logs et Monitoring

```bash
# Logs PostgreSQL
docker-compose logs postgres

# Logs MCP Server
docker-compose logs mcp-postgres-server

# Métriques système
docker stats crypto-postgres crypto-mcp-postgres

# Connexions actives
docker exec crypto-postgres psql -U crypto_user -d cryptoupdate -c "SELECT count(*) FROM pg_stat_activity;"
```

## Commandes de Maintenance

```bash
# Arrêter tous les services
docker-compose down

# Nettoyer et redémarrer
docker-compose down -v  # ⚠️ Supprime les volumes (données)
docker-compose up -d

# Mettre à jour les images
docker-compose pull
docker-compose up -d

# Redémarrer un service spécifique
docker-compose restart mcp-postgres-server

# Reconstruire l'image MCP
docker-compose build --no-cache mcp-postgres-server
```

## Support et Documentation

- **PostgreSQL**: https://www.postgresql.org/docs/
- **pgAdmin**: https://www.pgadmin.org/docs/
- **Docker Compose**: https://docs.docker.com/compose/
- **Redis**: https://redis.io/documentation