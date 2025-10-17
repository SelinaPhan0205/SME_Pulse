#!/bin/bash
set -e

# Create metastore_db database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE metastore_db;
    GRANT ALL PRIVILEGES ON DATABASE metastore_db TO $POSTGRES_USER;
EOSQL

echo "✅ Database metastore_db created!"
