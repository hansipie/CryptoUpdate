# MCP PostgreSQL Server Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from parent directory
COPY ../pyproject.toml ../uv.lock ./

# Install uv and Python dependencies
RUN pip install uv
RUN uv sync --frozen

# Add PostgreSQL-specific dependencies
RUN uv add psycopg2-binary asyncpg

# Copy application code from parent directory
COPY .. .

# Create necessary directories
RUN mkdir -p /app/logs && \
    chmod 755 /app/logs

# Expose MCP server port
EXPOSE 3000

# Set environment variables
ENV PYTHONPATH=/app
ENV POSTGRES_HOST=postgres
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=cryptoupdate
ENV POSTGRES_USER=crypto_user
ENV POSTGRES_PASSWORD=crypto_password

# Health check for PostgreSQL connection
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import psycopg2; psycopg2.connect(host='${POSTGRES_HOST}', port='${POSTGRES_PORT}', database='${POSTGRES_DB}', user='${POSTGRES_USER}', password='${POSTGRES_PASSWORD}').close()" || exit 1

# Default command - adjust based on your MCP server implementation
CMD ["uv", "run", "python", "-m", "mcp_postgres_server"]