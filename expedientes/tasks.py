"""
Tareas asíncronas de Celery para la automatización de conciliación.

Reemplaza el threading frágil por workers de fondo confiables.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def ejecutar_conciliacion(self, task_id):
    """
    Ejecuta el envío automático al portal de conciliación como tarea de Celery.

    Esta tarea es llamada desde la vista `enviar_conciliacion_automation`
    y se ejecuta en un worker de fondo, permitiendo que la request HTTP
    responda inmediatamente sin esperar a que termine el proceso (evita timeouts).

    Args:
        task_id: ID del registro TareaConciliacion en la BD
    """
    from .models import TareaConciliacion

    try:
        tarea = TareaConciliacion.objects.get(pk=task_id)
    except TareaConciliacion.DoesNotExist:
        logger.error('TareaConciliacion %s no encontrada', task_id)
        return {'error': 'Tarea no encontrada'}

    if tarea.estado in ('completado', 'fallido'):
        logger.warning('Tarea %s ya está %s, omitiendo', task_id, tarea.estado)
        return {'status': tarea.estado}

    # Marcar como ejecutando
    tarea.estado = 'ejecutando'
    tarea.save(update_fields=['estado'])

    logger.info('[Celery] Ejecutando tarea %s para expediente %s', task_id, tarea.expediente_id)

    from .conciliacion_automation import enviar_y_guardar

    try:
        # headless=True porque estamos en servidor (sin interfaz gráfica)
        resultado = enviar_y_guardar(
            expediente=tarea.expediente,
            usuario=tarea.usuario,
            headless=True,
        )

        if resultado.success:
            tarea.estado = 'completado'
            tarea.folio = resultado.folio or ''
            tarea.pdf_path = resultado.pdf_path or ''
            tarea.detalle = resultado.detalle or ''
            logger.info('[Celery] Tarea %s completada. Folio: %s', task_id, resultado.folio)
        else:
            tarea.estado = 'fallido'
            tarea.error = resultado.error or 'Error desconocido'
            tarea.detalle = resultado.detalle or ''
            logger.warning('[Celery] Tarea %s falló: %s', task_id, resultado.error[:100])

    except Exception as exc:
        logger.exception('[Celery] Error en tarea %s', task_id)

        # Reintentar si aún hay intentos disponibles
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        tarea.estado = 'fallido'
        tarea.error = f'{type(exc).__name__}: {exc}'
        tarea.detalle = 'Error después de reintentos'

    finally:
        tarea.completed_at = timezone.now()
        tarea.save(update_fields=['estado', 'folio', 'pdf_path', 'error', 'detalle', 'completed_at'])

    return {
        'status': tarea.estado,
        'folio': tarea.folio,
    }
