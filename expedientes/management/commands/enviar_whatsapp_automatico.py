"""
Management command para enviar mensajes de WhatsApp pendientes
que fueron generados automaticamente por cambios de estado.

Uso:
    uv run python manage.py enviar_whatsapp_automatico
    uv run python manage.py enviar_whatsapp_automatico --dry-run
    uv run python manage.py enviar_whatsapp_automatico --send-twilio

Por defecto usa deep_link (wa.me). Con --send-twilio usa la API de Twilio.
"""

from django.core.management.base import BaseCommand
from expedientes.models import WhatsAppMessage
from expedientes.whatsapp import enviar_whatsapp


class Command(BaseCommand):
    help = 'Envia mensajes de WhatsApp pendientes (generados automaticamente por cambios de estado)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra los mensajes pendientes sin enviarlos'
        )
        parser.add_argument(
            '--send-twilio',
            action='store_true',
            help='Envia via Twilio en lugar de deep_link (requiere configuracion)'
        )
        parser.add_argument(
            '--expediente',
            type=str,
            help='Numero de expediente especifico (ej: 2026-0011)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        use_twilio = options['send_twilio']
        expediente_filter = options['expediente']

        # Consultar mensajes pendientes
        qs = WhatsAppMessage.objects.filter(estado='pendiente').select_related(
            'expediente', 'expediente__cliente', 'enviado_por'
        ).order_by('created_at')

        if expediente_filter:
            qs = qs.filter(expediente__numero=expediente_filter)

        total = qs.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS('OK No hay mensajes pendientes.'))
            return

        self.stdout.write('Mensajes pendientes: %d' % total)
        self.stdout.write('   Dry run: %s' % ('Si' if dry_run else 'No'))
        self.stdout.write('   Metodo: %s' % ('Twilio API' if use_twilio else 'Deep Link (wa.me)'))
        self.stdout.write('-' * 60)

        # Prevenir race conditions: marcar como 'enviando' antes de procesar
        ids = list(qs.values_list('id', flat=True))
        WhatsAppMessage.objects.filter(id__in=ids).update(estado='enviando')

        enviados = 0
        fallidos = 0

        for msg in qs:
            expediente = msg.expediente
            cliente = expediente.cliente

            self.stdout.write('')
            self.stdout.write('  Caso: %s - %s' % (expediente.numero, cliente.nombre))
            self.stdout.write('     Tipo: %s' % msg.get_tipo_display())
            self.stdout.write('     Destino: %s' % msg.destino)
            self.stdout.write('     Mensaje: %s...' % msg.mensaje[:80])

            if dry_run:
                self.stdout.write(self.style.WARNING('     Dry-run: no se enviara'))
                continue

            # Determinar via de envio
            via = 'twilio' if use_twilio else 'deep_link'

            resultado = enviar_whatsapp(msg.destino, msg.mensaje, via=via)

            if resultado['success']:
                msg.estado = 'enviado'
                msg.via = resultado.get('via', via)
                msg.link_generado = resultado.get('link', '')
                msg.save()
                enviados += 1
                self.stdout.write(self.style.SUCCESS('     Enviado OK (%s)' % resultado['via']))
                if resultado.get('link'):
                    self.stdout.write('        Link: %s' % resultado['link'])
            else:
                msg.estado = 'fallido'
                msg.error_log = resultado.get('detail', 'Error desconocido')
                msg.save()
                fallidos += 1
                self.stdout.write(self.style.ERROR('     Fallido: %s' % resultado['detail']))

        # En caso de dry-run, restaurar los marcados como 'enviando' a 'pendiente'
        if dry_run:
            WhatsAppMessage.objects.filter(id__in=ids).update(estado='pendiente')

        # Resumen final
        self.stdout.write('')
        self.stdout.write('-' * 60)
        if dry_run:
            self.stdout.write(self.style.SUCCESS('Simulacion: %d mensaje(s) pendiente(s).' % total))
        else:
            resumen = 'Enviados: %d | Fallidos: %d | Total: %d' % (enviados, fallidos, enviados + fallidos)
            if fallidos > 0:
                self.stdout.write(self.style.WARNING(resumen))
            else:
                self.stdout.write(self.style.SUCCESS(resumen))
