"""
Management Command: enviar_solicitud_conciliacion
=================================================
Envía una solicitud de conciliación al portal del Centro de Conciliación
Laboral de Baja California (app.conciliacionbc.gob.mx).

Llena automáticamente el formulario con los datos del expediente,
captura el folio generado y descarga el PDF.

Uso:
    # Enviar un expediente específico (muestra navegador para debug)
    uv run python manage.py enviar_solicitud_conciliacion 42

    # Enviar varios expedientes en lote (headless, sin interfaz gráfica)
    uv run python manage.py enviar_solicitud_conciliacion 42 58 73 --headless

    # Simular (solo mostrar qué datos se llenarían, sin enviar)
    uv run python manage.py enviar_solicitud_conciliacion 42 --dry-run

    # Enviar todos los expedientes en estado 'solicitud' sin folio
    uv run python manage.py enviar_solicitud_conciliacion --pendientes --headless
"""
import logging

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from expedientes.models import Expediente

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Envía solicitud de conciliación al portal de Baja California'

    def add_arguments(self, parser):
        parser.add_argument(
            'expediente_ids',
            nargs='*',
            type=int,
            help='IDs de expedientes a enviar (separados por espacio)',
        )
        parser.add_argument(
            '--headless',
            action='store_true',
            default=False,
            help='Ejecutar sin interfaz gráfica del navegador',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Solo mostrar qué datos se enviarían, sin ejecutar la automatización',
        )
        parser.add_argument(
            '--pendientes',
            action='store_true',
            default=False,
            help='Enviar todos los expedientes en estado "solicitud" o "nuevo" sin folio',
        )
        parser.add_argument(
            '--download-dir',
            type=str,
            default=None,
            help='Directorio donde guardar los PDFs descargados',
        )

    def handle(self, *args, **options):
        headless = options['headless']
        dry_run = options['dry_run']
        download_dir = options.get('download_dir')

        # Obtener expedientes
        expedientes = []

        if options['pendientes']:
            expedientes = list(Expediente.objects.filter(
                estado__in=['solicitud', 'nuevo'],
            ).filter(
                Q(folio__isnull=True) | Q(folio__exact='')
            ).select_related('cliente')[:10])
            if not expedientes:
                self.stdout.write(self.style.WARNING('No hay expedientes pendientes por enviar.'))
                return

        elif options['expediente_ids']:
            for eid in options['expediente_ids']:
                try:
                    exp = Expediente.objects.select_related('cliente').get(pk=eid)
                    expedientes.append(exp)
                except Expediente.DoesNotExist:
                    self.stderr.write(f'Expediente {eid} no encontrado. Ignorando.')

        else:
            self.print_help('manage.py', 'enviar_solicitud_conciliacion')
            return

        # Mostrar resumen
        self.stdout.write(self.style.SUCCESS(
            f'\n{"=" * 60}'
            f'\n  Enviando {len(expedientes)} expediente(s) al portal de conciliación'
            f'\n  Modo headless: {"SÍ" if headless else "NO"}'
            f'\n  Dry-run: {"SÍ" if dry_run else "NO"}'
            f'\n{"=" * 60}\n'
        ))

        if dry_run:
            self._dry_run(expedientes)
            return

        # Ejecutar automatización
        from expedientes.conciliacion_automation import enviar_y_guardar

        exitos = 0
        fallos = 0

        for i, exp in enumerate(expedientes, 1):
            self.stdout.write(f'\n[{i}/{len(expedientes)}] Procesando {exp.numero} ({exp.cliente.nombre})...')

            try:
                resultado = enviar_y_guardar(exp, headless=headless)

                if resultado.success:
                    self.stdout.write(self.style.SUCCESS(
                        f'  OK - Enviado: Folio={resultado.folio or "N/A"}, PDF={resultado.pdf_path or "N/A"}'
                    ))
                    exitos += 1
                else:
                    self.stdout.write(self.style.ERROR(
                        f'  FALLO: {resultado.error or "Error desconocido"}'
                    ))
                    fallos += 1

            except Exception as e:
                logger.exception(f'Error procesando {exp.numero}')
                self.stderr.write(f'  ERROR: {e}')
                fallos += 1

        # Resumen final
        self.stdout.write(f'\n{"=" * 60}')
        self.stdout.write(
            self.style.SUCCESS(f'  Completado: {exitos} exitosos, {fallos} fallos')
            if not fallos else
            self.style.WARNING(f'  Completado con errores: {exitos} exitosos, {fallos} fallos')
        )
        self.stdout.write(f'{"=" * 60}\n')

    def _dry_run(self, expedientes):
        """Muestra qué datos se enviarían sin ejecutar la automatización."""
        for exp in expedientes:
            cl = exp.cliente
            solicitud = getattr(exp, 'solicitud', None)
            self.stdout.write(f'\n--- {exp.numero} ---')
            self.stdout.write(f'  Cliente: {cl.nombre}')
            self.stdout.write(f'  CURP: {cl.curp}')
            self.stdout.write(f'  Teléfono: {cl.telefono}')
            self.stdout.write(f'  Dirección: {cl.direccion_calle} #{cl.direccion_numero}, {cl.direccion_colonia}')
            self.stdout.write(f'  Empresa: {cl.empresa}')
            self.stdout.write(f'  Actividad: {cl.empresa_actividad}')
            self.stdout.write(f'  Puesto: {cl.puesto}')
            self.stdout.write(f'  Salario: ${cl.salario}')
            fec_ingreso = str(cl.fecha_ingreso or 'N/A')
            fec_salida = str(cl.fecha_salida or 'N/A')
            self.stdout.write(f'  Ingreso/Salida: {fec_ingreso} -> {fec_salida}')
            self.stdout.write(f'  Prestaciones: {exp.prestaciones_reclamadas or "—"}')
            if solicitud:
                self.stdout.write(f'  Objeto(s): {", ".join(solicitud.get_objetos_lista()) or "—"}')
