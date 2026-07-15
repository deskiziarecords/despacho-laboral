#!/bin/sh
set -e

echo "=== Despacho Laboral - Iniciando ==="

# 1. Migraciones
echo ">>> Ejecutando migraciones..."
uv run python manage.py migrate --noinput

# 2. Migrar datos de SQLite a PostgreSQL (si hay cambio de base de datos)
echo ">>> Verificando migración SQLite → PostgreSQL..."
uv run python manage.py migrate_sqlite_to_pg 2>&1 || echo ">>> (Aviso: no se pudo migrar datos de SQLite — consulta logs para más detalles)"

# 3. Crear superusuario admin (si no existe)
echo ">>> Verificando superusuario..."
export DJANGO_SUPERUSER_PASSWORD="${DJANGO_SUPERUSER_PASSWORD:-Admin123!}"
uv run python manage.py createsuperuser --noinput \
    --username "${DJANGO_SUPERUSER_USERNAME:-admin}" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@despacho.com}" \
    || echo ">>> (Superusuario ya existe u otro error ignorado)"

# Actualizar el rol del superusuario a superadmin
# (el signal post_save crea el perfil con rol='asesor' por defecto)
echo ">>> Actualizando rol del superusuario a superadmin..."
uv run python manage.py shell -c "
from django.contrib.auth.models import User
username = '${DJANGO_SUPERUSER_USERNAME:-admin}'
try:
    user = User.objects.get(username=username)
    if hasattr(user, 'profile'):
        if user.profile.rol != 'superadmin':
            user.profile.rol = 'superadmin'
            user.profile.save()
            print(f'>>> Perfil de {username} actualizado a superadmin')
        else:
            print(f'>>> Perfil de {username} ya es superadmin')
    else:
        print(f'>>> Advertencia: {username} no tiene perfil')
except User.DoesNotExist:
    print(f'>>> Advertencia: usuario {username} no encontrado')
" || echo ">>> (Aviso: no se pudo actualizar el rol del superusuario)"

# 4. Resincronizar sequences de PostgreSQL
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

# 5. Crear usuarios de prueba (idempotente — omite si ya existen)
echo ">>> Creando usuarios de prueba..."
uv run python manage.py crear_usuarios_prueba 2>&1 || echo ">>> (Aviso: no se pudieron crear usuarios de prueba — consulta los logs para más detalles)"

# 6. Sembrar datos de prueba (idempotente — omite si ya existen)
echo ">>> Sembrando datos de prueba..."
uv run python manage.py seed_datos 2>&1 || echo ">>> (Aviso: no se pudieron sembrar datos de prueba — consulta los logs para más detalles)"

# 7. Iniciar servicio según SERVICE_TYPE
# SERVICE_TYPE=worker → Celery Worker
# SERVICE_TYPE=web o por defecto → Gunicorn
if [ "${SERVICE_TYPE:-web}" = "worker" ]; then
    echo ">>> Iniciando Celery Worker..."
    exec uv run celery -A config worker --loglevel=info --concurrency=1
elif [ "${SERVICE_TYPE:-web}" = "beat" ]; then
    echo ">>> Iniciando Celery Beat..."
    exec uv run celery -A config beat --loglevel=info
else
    echo ">>> Iniciando Gunicorn en 0.0.0.0:${PORT:-8000}..."
    exec uv run gunicorn config.wsgi:application \
        --bind "0.0.0.0:${PORT:-8000}" \
        --workers 3 \
        --timeout 120
fi
