#!/bin/sh
set -e

echo "=== Despacho Laboral - Iniciando ==="

# 1. Migraciones
echo ">>> Ejecutando migraciones..."
uv run python manage.py migrate --noinput

# 2. Crear superusuario admin (si no existe)
echo ">>> Verificando superusuario..."
export DJANGO_SUPERUSER_PASSWORD="${DJANGO_SUPERUSER_PASSWORD:-Admin123!}"
uv run python manage.py createsuperuser --noinput \
    --username "${DJANGO_SUPERUSER_USERNAME:-admin}" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@despacho.com}" \
    || echo ">>> (Superusuario ya existe u otro error ignorado)"

# 3. Resincronizar sequences de PostgreSQL
# Después de migrar datos desde SQLite, los auto-increment sequences
# de PostgreSQL pueden quedar desincronizados. Esto previene errores
# de "duplicate key value violates unique constraint" al crear registros.
echo ">>> Resincronizando sequences..."
uv run python -c "
from django.apps import apps
from django.core.management import call_command
from io import StringIO
from django.db import connection

app_labels = [app.label for app in apps.get_app_configs()]
out = StringIO()
call_command('sqlsequencereset', *app_labels, stdout=out)
sql = out.getvalue()
if sql.strip():
    with connection.cursor() as cursor:
        cursor.execute(sql)
    print('>>> Sequences resincronizadas correctamente.')
else:
    print('>>> No se necesita resincronización.')
" || echo ">>> (Aviso: no se pudieron resincronizar sequences, ignorando)"

# 4. Iniciar Gunicorn
echo ">>> Iniciando Gunicorn en 0.0.0.0:${PORT:-8000}..."
exec uv run gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 3 \
    --timeout 120
