#!/bin/bash
set -e

# Function to wait for postgres
wait_for_postgres() {
    echo "Waiting for PostgreSQL..."
    while ! nc -z postgres 5432; do
        sleep 1
    done
    echo "PostgreSQL is ready!"
}

# Function to initialize database (chỉ chạy 1 lần)
init_airflow() {
    if [ ! -f /opt/airflow/.airflow_db_initialized ]; then
        echo "=========================================="
        echo "Initializing Airflow Database..."
        echo "=========================================="
        
        airflow db migrate
        
        airflow users create \
            --username admin \
            --firstname Admin \
            --lastname User \
            --role Admin \
            --email admin@example.com \
            --password admin 2>/dev/null || echo "✓ Admin already exists"
        
        touch /opt/airflow/.airflow_db_initialized
        echo "Database initialized!"
    else
        echo "Database already initialized, skipping..."
    fi
}

# Main logic
case "$1" in
    webserver)
        wait_for_postgres
        init_airflow
        echo "Starting Airflow Webserver..."
        exec airflow webserver
        ;;
    scheduler)
        wait_for_postgres
        # Scheduler cũng check init, nhưng không gây conflict vì có flag file
        init_airflow
        echo "Starting Airflow Scheduler..."
        exec airflow scheduler
        ;;
    *)
        # Fallback: execute command truyền vào
        exec "$@"
        ;;
esac