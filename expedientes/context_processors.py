from .models import Notificacion


def notificaciones_globales(request):
    """
    Context processor que agrega las notificaciones no leídas del usuario actual
    para mostrarlas en el icono de campana del header.
    """
    if not request.user.is_authenticated:
        return {}

    notificaciones = Notificacion.objects.filter(
        usuario=request.user
    ).order_by('-created_at')[:10]

    no_leidas = sum(1 for n in notificaciones if not n.leida)

    return {
        'notificaciones': notificaciones,
        'notificaciones_no_leidas': no_leidas,
    }
