#!/bin/sh
set -e

echo "Rodando migrations..."
python manage.py migrate --noinput

exec "$@"
