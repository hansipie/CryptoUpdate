#!/bin/bash

# PostgreSQL Restore Script for CryptoUpdate MCP
# Usage: ./restore.sh <backup_file> [database_name]

set -e

# Configuration
CONTAINER_NAME="crypto-postgres"
DEFAULT_DB="cryptoupdate"
DEFAULT_USER="crypto_user"

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file> [database_name]"
    echo "Example: $0 ./backups/cryptoupdate_20241227_143022.sql.gz"
    echo "Example: $0 ./backups/cryptoupdate_20241227_143022.sql.gz testdb"
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME=${2:-$DEFAULT_DB}

# Validate backup file
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file '$BACKUP_FILE' not found"
    exit 1
fi

echo "Restoring database: $DB_NAME"
echo "From backup file: $BACKUP_FILE"

# Check if container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "Error: PostgreSQL container '$CONTAINER_NAME' is not running"
    echo "Start it with: docker-compose up -d postgres"
    exit 1
fi

# Confirmation prompt
read -p "This will overwrite the database '$DB_NAME'. Are you sure? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled"
    exit 0
fi

# Create database if it doesn't exist
echo "Ensuring database exists..."
docker exec "$CONTAINER_NAME" psql -U "$DEFAULT_USER" -d postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true

# Drop existing connections to the database
echo "Dropping existing connections..."
docker exec "$CONTAINER_NAME" psql -U "$DEFAULT_USER" -d postgres -c "
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DB_NAME'
  AND pid <> pg_backend_pid();"

# Restore from backup
echo "Restoring from backup..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    # Compressed backup
    if gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DEFAULT_USER" -d "$DB_NAME"; then
        echo "Restore completed successfully from compressed backup"
    else
        echo "Error: Restore failed"
        exit 1
    fi
else
    # Uncompressed backup
    if docker exec -i "$CONTAINER_NAME" psql -U "$DEFAULT_USER" -d "$DB_NAME" < "$BACKUP_FILE"; then
        echo "Restore completed successfully from uncompressed backup"
    else
        echo "Error: Restore failed"
        exit 1
    fi
fi

# Verify restore
echo "Verifying restore..."
TABLE_COUNT=$(docker exec "$CONTAINER_NAME" psql -U "$DEFAULT_USER" -d "$DB_NAME" -t -c "
SELECT COUNT(*) 
FROM information_schema.tables 
WHERE table_schema NOT IN ('information_schema', 'pg_catalog');" | tr -d ' ')

echo "Database '$DB_NAME' restored successfully with $TABLE_COUNT tables"

# Show database info
echo "Database information:"
docker exec "$CONTAINER_NAME" psql -U "$DEFAULT_USER" -d "$DB_NAME" -c "
SELECT 
    schemaname,
    COUNT(*) as table_count
FROM pg_tables 
WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
GROUP BY schemaname
ORDER BY schemaname;"

echo "Restore process completed successfully!"