import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import Expediente, Documento, Movimiento, Nota, WhatsAppMessage, TareaConciliacion

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Expediente)
def track_estado_change(sender, instance, **kwargs):
    """Guarda el estado anterior antes de guardar."""
    if instance.pk:
        try:
            instance._previous_estado = Expediente.objects.get(pk=instance.pk).estado
        except Expediente.DoesNotExist:
            instance._previous_estado = None
    else:
        instance._previous_estado = None


@receiver(post_save, sender=Expediente)
def auto_generar_whatsapp_por_estado(sender, instance, created, **kwargs):
    """
    Cuando un expediente cambia de estado y tiene notificaciones automáticas activadas,
    genera un mensaje de WhatsApp en estado 'pendiente' para que el management command
    lo procese posteriormente.
    """
    # Solo si el estado cambió
    previous = getattr(instance, '_previous_estado', None)
    if previous is None or previous == instance.estado:
        return

    # Solo si tiene notificaciones automáticas activadas
    if not instance.notificar_whatsapp_auto:
        return

    # Solo si tiene un cliente con número de contacto
    destino = instance.cliente.whatsapp or instance.cliente.telefono
    if not destino:
        return

    try:
        from .whatsapp import generar_mensaje_automatico

        resultado = generar_mensaje_automatico(instance)
        if not resultado:
            return

        # Crear el mensaje como pendiente
        WhatsAppMessage.objects.create(
            expediente=instance,
            destino=resultado['destino'],
            mensaje=resultado['mensaje'],
            tipo=resultado['tipo'],
            via='deep_link',
            estado='pendiente',
            enviado_por=instance.asesor,
            link_generado='',
            error_log=f'Auto-generado por cambio de estado: {previous} → {instance.estado}',
        )

        logger.info(
            f'WhatsApp auto-generado para {instance.numero}: '
            f'{previous} → {instance.estado} ({resultado["tipo"]})'
        )

    except Exception as e:
        logger.error(f'Error generando WhatsApp automático para {instance.numero}: {e}')


@receiver(post_save, sender=Documento)
def log_documento_upload(sender, instance, created, **kwargs):
    """Registra la subida de documentos."""
    if created:
        Movimiento.objects.create(
            expediente=instance.expediente,
            usuario=instance.subido_por,
            accion='subida_documento',
            detalle=f'Documento subido: {instance.descripcion} ({instance.get_tipo_display()})',
        )


@receiver(post_save, sender=Nota)
def log_nota_creada(sender, instance, created, **kwargs):
    """Registra la creación de notas."""
    if created:
        Movimiento.objects.create(
            expediente=instance.expediente,
            usuario=instance.usuario,
            accion='nota_agregada',
            detalle=f'Nota agregada: {instance.contenido[:100]}...',
        )


def registrar_movimiento(expediente, usuario, accion, detalle=''):
    """Función helper para registrar movimientos desde las vistas."""
    Movimiento.objects.create(
        expediente=expediente,
        usuario=usuario,
        accion=accion,
        detalle=detalle,
    )


# ─── Tracker de cambios de estado para TareaConciliación ───────────────────

@receiver(pre_save, sender=TareaConciliacion)
def track_tarea_conciliacion_estado(sender, instance, **kwargs):
    """Guarda el estado anterior antes de guardar para evitar notificaciones duplicadas."""
    if instance.pk:
        try:
            instance._previous_estado = TareaConciliacion.objects.get(pk=instance.pk).estado
        except TareaConciliacion.DoesNotExist:
            instance._previous_estado = None
    else:
        instance._previous_estado = None


# ─── Notificación por correo de TareaConciliación ────────────────────────

@receiver(post_save, sender=TareaConciliacion)
def notificar_conciliacion_por_email(sender, instance, **kwargs):
    """
    Cuando una tarea de conciliación cambia a 'completado' o 'fallido',
    envía un correo de notificación al usuario que la inició.
    """
    # Solo notificar cuando el estado cambió a un estado terminal
    previous = getattr(instance, '_previous_estado', None)
    if previous == instance.estado:
        return  # No hubo cambio real, omitir para evitar duplicados

    if instance.estado not in ('completado', 'fallido'):
        return

    # Solo si tiene completed_at (es un estado terminal post-ejecución)
    if not instance.completed_at:
        return

    # Determinar destinatario: primero el usuario que inició la tarea,
    # luego el asesor del expediente como fallback
    destinatario = instance.usuario or instance.expediente.asesor
    if not destinatario or not destinatario.email:
        logger.warning(
            'No se pudo enviar notificación de conciliación: '
            'usuario sin email para tarea %s', instance.pk
        )
        return

    # Preparar contexto para la plantilla
    es_exitoso = instance.estado == 'completado'
    expediente = instance.expediente

    contexto = {
        'usuario_nombre': destinatario.get_full_name() or destinatario.username,
        'expediente_numero': expediente.numero,
        'cliente_nombre': expediente.cliente.nombre,
        'resultado': 'sido COMPLETADO exitosamente ✅' if es_exitoso else 'FALLADO ❌',
        'folio': instance.folio or '',
        'error': instance.error or '',
        'detalle': instance.detalle or '',
        'fecha_inicio': instance.created_at.strftime('%d/%m/%Y %H:%M'),
        'tiempo_total': instance.tiempo_transcurrido(),
        'expediente_url': '',
    }

    # Construir URL del expediente (absoluta si es posible)
    try:
        from django.contrib.sites.models import Site
        dominio = Site.objects.get_current().domain
        ruta = reverse('expediente_detail', kwargs={'pk': expediente.pk})
        contexto['expediente_url'] = f'https://{dominio}{ruta}'
    except Exception:
        ruta = reverse('expediente_detail', kwargs={'pk': expediente.pk})
        contexto['expediente_url'] = f'https://despacho-laboral-production.up.railway.app{ruta}'

    # Asunto del correo
    asunto = (
        f'✅ Conciliación completada — {expediente.numero}'
        if es_exitoso
        else f'❌ Conciliación fallida — {expediente.numero}'
    )

    # Renderizar plantilla de texto plano
    mensaje_texto = render_to_string('expedientes/email_conciliacion.txt', contexto)

    try:
        send_mail(
            subject=asunto,
            message=mensaje_texto,
            from_email=None,  # usa DEFAULT_FROM_EMAIL de settings
            recipient_list=[destinatario.email],
            fail_silently=False,
        )
        logger.info(
            'Notificación de conciliación enviada a %s para tarea %s (estado: %s)',
            destinatario.email, instance.pk, instance.estado
        )
    except Exception as e:
        logger.warning(
            'Error enviando notificación de conciliación a %s: %s',
            destinatario.email, e
        )
