import os

from celery import Celery

# Django settings module por defecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('despacho_laboral')

# Usar Redis como broker y backend de resultados
# Railway inyecta REDIS_URL automáticamente; fallback local
REDIS_URL = os.environ.get(
    'REDIS_URL',
    os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
)

app.conf.broker_url = REDIS_URL
app.conf.result_backend = REDIS_URL

# Namespace CELERY_ para que settings.py pueda configurar más opciones
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubrir tareas en todos los apps registrados
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tarea de depuración para verificar que Celery funciona."""
    print(f'🔧 Celery debug task: {self.request!r}')
