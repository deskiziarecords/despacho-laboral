#!/bin/sh
set -e

echo "=== Despacho Laboral - Iniciando ==="

# 1. Migraciones
echo ">>> Ejecutando migraciones..."
uv run python manage.py migrate --noinput

# 3. Crear superusuario admin (si no existe)
echo ">>> Verificando superusuario..."
DJANGO_SUPERUSER_PASSWORD="${DJANGO_SUPERUSER_PASSWORD:-Admin123!}"
uv run python manage.py createsuperuser --noinput \
    --username "${DJANGO_SUPERUSER_USERNAME:-admin}" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@despacho.com}" \
    2>/dev/null || true

# 4. Iniciar Gunicorn
echo ">>> Iniciando Gunicorn en 0.0.0.0:${PORT:-8000}..."
exec uv run gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 3 \
    --timeout 120
