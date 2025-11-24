#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; do
  sleep 1
done

echo "PostgreSQL is ready!"

# Only run migrations and collectstatic for the backend service (gunicorn)
# Celery and Celery Beat should skip these steps
if [[ "$1" == "gunicorn"* ]]; then
  echo "Creating migrations..."
  python manage.py makemigrations --noinput || true

  echo "Running migrations..."
  python manage.py migrate --noinput

  echo "Collecting static files..."
  python manage.py collectstatic --noinput --clear
fi

exec "$@"
