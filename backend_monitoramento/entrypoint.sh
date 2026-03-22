#!/bin/sh
set -e

echo "Rodando migrations..."
python manage.py migrate --noinput

echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear

exec "$@"
