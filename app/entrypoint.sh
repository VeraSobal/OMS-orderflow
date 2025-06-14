#!/bin/sh

echo "Apply migrations"

python manage.py migrate --no-input

echo "Create superuser"

python manage.py createsuperuser --noinput

echo "Load directories"

python manage.py loaddata directories

echo "Starting Celery Worker..."
celery -A config worker --loglevel=info &

echo "Starting Celery Beat..."
celery -A config beat --loglevel=info &

echo "Starting Django Server..."
exec "$@"