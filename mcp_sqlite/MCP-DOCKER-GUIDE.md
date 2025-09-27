# MCP SQLite Server Docker Setup

This guide explains how to dockerize and run your MCP SQLite server.

## Quick Start

### 1. Build and Run with Docker Compose

```bash
# Build and start the MCP SQLite server
docker-compose -f docker-compose.mcp.yml up -d

# View logs
docker-compose -f docker-compose.mcp.yml logs -f mcp-sqlite-server

# Stop the services
docker-compose -f docker-compose.mcp.yml down
```

### 2. Build and Run with Docker Only

```bash
# Build the MCP server image
docker build -f Dockerfile.mcp -t crypto-mcp-sqlite .

# Run the container
docker run -d \
  --name crypto-mcp-sqlite \
  -p 3000:3000 \
  -v $(pwd)/data:/app/data \
  -e MCP_SQLITE_DB_PATH=/app/data/db.sqlite3 \
  crypto-mcp-sqlite
```

## Configuration

### Environment Variables

- `MCP_SQLITE_DB_PATH`: Path to SQLite database (default: `/app/data/db.sqlite3`)
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `PYTHONPATH`: Python path (default: `/app`)

### Ports

- `3000`: MCP SQLite server port
- `3001`: SQLite browser (optional, for database management)

### Volumes

- `./data:/app/data`: SQLite database persistence
- `./logs:/app/logs`: Log files (optional)

## Database Management

### Using SQLite Browser (Web Interface)

Access the SQLite browser at `http://localhost:3001` to manage your database through a web interface.

### Direct Database Access

```bash
# Connect to running container
docker exec -it crypto-mcp-sqlite bash

# Access SQLite database directly
sqlite3 /app/data/db.sqlite3
```

## Development

### Local Development with Docker

```bash
# Build development image
docker build -f Dockerfile.mcp -t crypto-mcp-sqlite:dev .

# Run with development settings
docker run -it --rm \
  -p 3000:3000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd):/app \
  -e LOG_LEVEL=DEBUG \
  crypto-mcp-sqlite:dev
```

### Debugging

```bash
# View container logs
docker logs crypto-mcp-sqlite

# Check container health
docker inspect crypto-mcp-sqlite --format='{{.State.Health.Status}}'

# Access container shell
docker exec -it crypto-mcp-sqlite bash
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure SQLite database file exists in `./data/db.sqlite3`
   - Check file permissions on the data directory
   - Verify volume mounting is correct

2. **Port Conflicts**
   - Change port mapping if 3000 is already in use: `-p 3001:3000`

3. **Permission Issues**
   - Ensure data directory is writable: `chmod 755 ./data`

### Health Checks

The container includes a health check that verifies SQLite database connectivity:

```bash
# Check health status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## Security Considerations

- SQLite database is mounted as volume for persistence
- Container runs with minimal privileges
- Resource limits are configured in docker-compose
- No sensitive data is exposed in environment variables

## Performance Tuning

### Resource Limits

Adjust in `docker-compose.mcp.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 1G        # Increase for larger databases
      cpus: '1.0'       # Increase for heavy workloads
```

### SQLite Optimization

Add SQLite pragmas in your MCP server configuration:

```python
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
```

## Monitoring

### Logs

```bash
# Follow logs in real-time
docker-compose -f docker-compose.mcp.yml logs -f

# View specific service logs
docker-compose -f docker-compose.mcp.yml logs mcp-sqlite-server
```

### Health Monitoring

```bash
# Check container health
docker inspect crypto-mcp-sqlite | jq '.[0].State.Health'
```

## Backup and Restore

### Database Backup

```bash
# Create backup
docker exec crypto-mcp-sqlite sqlite3 /app/data/db.sqlite3 ".backup /app/data/backup_$(date +%Y%m%d_%H%M%S).sqlite3"

# Copy backup to host
docker cp crypto-mcp-sqlite:/app/data/backup_*.sqlite3 ./data/
```

### Database Restore

```bash
# Copy backup to container
docker cp ./data/backup.sqlite3 crypto-mcp-sqlite:/app/data/

# Restore database
docker exec crypto-mcp-sqlite sqlite3 /app/data/db.sqlite3 ".restore /app/data/backup.sqlite3"
```