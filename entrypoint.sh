#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
while ! python -c "import psycopg; psycopg.connect('host=$POSTGRES_HOST port=$POSTGRES_PORT dbname=$POSTGRES_DB user=$POSTGRES_USER password=$POSTGRES_PASSWORD')" 2>/dev/null; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 1
done
echo "PostgreSQL is up - continuing..."

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files (if needed for production)
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Execute the main command
exec "$@"
