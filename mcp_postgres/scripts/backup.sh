#!/bin/bash

# PostgreSQL Backup Script for CryptoUpdate MCP
# Usage: ./backup.sh [database_name]

set -e

# Configuration
BACKUP_DIR="./backups"
CONTAINER_NAME="crypto-postgres"
DEFAULT_DB="cryptoupdate"
DEFAULT_USER="crypto_user"
RETENTION_DAYS=7

# Use provided database name or default
DB_NAME=${1:-$DEFAULT_DB}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_$TIMESTAMP.sql.gz"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "Starting backup of database: $DB_NAME"
echo "Backup will be saved to: $BACKUP_FILE"

# Check if container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "Error: PostgreSQL container '$CONTAINER_NAME' is not running"
    echo "Start it with: docker-compose up -d postgres"
    exit 1
fi

# Create backup
echo "Creating backup..."
if docker exec "$CONTAINER_NAME" pg_dump -U "$DEFAULT_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"; then
    echo "Backup completed successfully: $BACKUP_FILE"
    
    # Get backup size
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup size: $BACKUP_SIZE"
else
    echo "Error: Backup failed"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Cleanup old backups
echo "Cleaning up old backups (keeping last $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete

# List recent backups
echo "Recent backups:"
ls -lh "$BACKUP_DIR"/${DB_NAME}_*.sql.gz | tail -5

echo "Backup process completed successfully!"