#!/bin/bash
set -e

echo "🚀 Starting Airflow initialization..."

# Wait for Postgres
echo "⏳ Waiting for Postgres..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "✅ Postgres is ready!"

# Initialize database
echo "📊 Initializing Airflow database..."
airflow db init || true

# Run migrations
echo "🔄 Running database migrations..."
airflow db migrate

# Create admin user
echo "👤 Creating admin user..."
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com || echo "User already exists"

# Start scheduler in background
echo "📅 Starting Airflow scheduler..."
airflow scheduler &

# Start webserver (foreground)
echo "🌐 Starting Airflow webserver..."
exec airflow webserver
