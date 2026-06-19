import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Expediente, Documento, Movimiento, Nota, WhatsAppMessage

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
