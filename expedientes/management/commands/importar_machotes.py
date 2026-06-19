"""
Comando de gestión: importar_machotes
======================================

Importa archivos .docx de la carpeta demandas/ y los convierte
en Machotes (plantillas HTML reutilizables) en la base de datos.

Uso:
    uv run python manage.py importar_machotes
    uv run python manage.py importar_machotes --reload   # Re-importa todos
    uv run python manage.py importar_machotes --file "Demanda XYZ.docx"
"""

import os
import re
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from docx import Document

from expedientes.models import Machote


# ─── Mapeo de archivos a categorías ──────────────────────────────────────

# Reglas para clasificar archivos automáticamente
PATRONES_CATEGORIA = [
    (r'(?i)demanda', 'demanda'),
    (r'(?i)carta\s*finiquito', 'carta_finiquito'),
    (r'(?i)convenio', 'convenio'),
    (r'(?i)solicitud\s*conciliacion', 'solicitud'),
    (r'(?i)solicitud.*conciliaci', 'solicitud'),
    (r'(?i)citatorio', 'citatorio'),
]

PATRONES_JURISDICCION = [
    (r'(?i)federal', 'federal'),
    (r'(?i)baja\s*california|estatal', 'estatal'),
]

PATRONES_TIPO_DESPIDO = [
    (r'(?i)injustificado', 'injustificado'),
    (r'(?i)justificado', 'justificado'),
    (r'(?i)voluntario|renuncia', 'voluntario'),
    (r'(?i)rescisi', 'rescision'),
]


def clasificar_archivo(nombre_archivo: str) -> dict:
    """Clasifica un archivo según su nombre."""
    resultado = {
        'categoria': 'otro',
        'jurisdiccion': 'federal',
        'tipo_despido': None,
        'nombre_legible': os.path.splitext(nombre_archivo)[0].strip(),
    }

    for patron, categoria in PATRONES_CATEGORIA:
        if re.search(patron, nombre_archivo):
            resultado['categoria'] = categoria
            break

    for patron, jurisdiccion in PATRONES_JURISDICCION:
        if re.search(patron, nombre_archivo):
            resultado['jurisdiccion'] = jurisdiccion
            break

    for patron, tipo_despido in PATRONES_TIPO_DESPIDO:
        if re.search(patron, nombre_archivo):
            resultado['tipo_despido'] = tipo_despido
            break

    return resultado


def extraer_nombre_plantilla(nombre_archivo: str) -> str:
    """Extrae un nombre legible del archivo."""
    nombre = os.path.splitext(nombre_archivo)[0]
    # Limpiar prefijos comunes
    nombre = re.sub(r'^(Demanda|Carta|Convenio|Solicitud)\s*', '', nombre, flags=re.I)
    # Limpiar VS y sufijos
    nombre = re.sub(r'\s+VS\s+.*', '', nombre, flags=re.I)
    # Limpiar extras
    nombre = re.sub(r'\s*—\s*(Federal|General|Aplicación General|Baja California).*', '', nombre, flags=re.I)
    nombre = nombre.strip()
    # Si quedó vacío, usar el nombre original
    if not nombre:
        nombre = os.path.splitext(nombre_archivo)[0]
    return nombre


def docx_a_html(docx_path: str) -> str:
    """Convierte un documento .docx a HTML básico con estructura legal."""
    doc = Document(docx_path)
    html_parts = []
    in_table = False

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style = para.style.name if para.style else 'Normal'

        # Detectar encabezados
        if style.startswith('Heading 1') or style.startswith('Title'):
            html_parts.append(f'<h2>{_escape_html(text)}</h2>')
        elif style.startswith('Heading 2'):
            html_parts.append(f'<h3>{_escape_html(text)}</h3>')
        elif style.startswith('Heading 3'):
            html_parts.append(f'<h4>{_escape_html(text)}</h4>')
        elif style.startswith('List') or text.startswith('•') or text.startswith('-'):
            html_parts.append(f'<li>{_escape_html(text.lstrip("•- "))}</li>')
        else:
            # Detectar si parece un título de sección legal
            if re.match(r'^[—\-]\s*[A-ZÁÉÍÓÚÑ\s]+\s*[—\-]', text):
                html_parts.append(f'<h3 style="color:#1F2937;">{_escape_html(text)}</h3>')
            # Detectar puntos petitorios / hechos numerados
            elif re.match(r'^(PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO)\b', text, re.I):
                html_parts.append(f'<p><strong>{_escape_html(text.split(".-")[0])}.-</strong>{_escape_html(text.split(".-", 1)[1] if ".-" in text else text.split(".", 1)[1] if "." in text else "")}</p>')
            elif re.match(r'^(I|II|III|IV|V|VI|VII|VIII|IX|X)\.-', text):
                html_parts.append(f'<p><strong>{_escape_html(text.split(".-")[0])}.-</strong>{_escape_html(text.split(".-", 1)[1] if ".-" in text else "")}</p>')
            else:
                html_parts.append(f'<p>{_escape_html(text)}</p>')

    html = '\n'.join(html_parts)

    # Envolver en estructura básica si no tiene encabezados
    if not html.startswith('<h2'):
        html = f'<h2 style="text-align:center;color:#1F2937;">ESCRITO INICIAL DE DEMANDA</h2>\n<hr style="border:none;border-top:1px solid #1D4ED8;width:70%;margin:10px auto;">\n{html}'

    return html


def _escape_html(text: str) -> str:
    """Escapa caracteres HTML básicos."""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    return text


def reemplazar_datos_con_marcadores(html: str) -> str:
    """
    Reemplaza datos específicos de clientes con marcadores
    para que la plantilla sea reutilizable.
    """
    # Reemplazar nombres completos de personas
    # Buscar patrones de nombre completo (Nombre Apellido Apellido o similar)
    sustituciones = [
        # Fechas comunes
        (r'\b\d{1,2}\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+\d{4}\b', '{{ fecha }}'),
        (r'\b\d{4}-\d{2}-\d{2}\b', '{{ fecha }}'),

        # Salarios (formato moneda)
        (r'\$\s*[\d,]+\.?\d*\s*(mensuales|semanales|diarios|quincenales)?', '{{ salario }} {{ periodo_pago }}'),

        # Números de teléfono
        (r'\+?\d{10,15}', '{{ telefono }}'),

        # CURP (18 caracteres alfanuméricos)
        (r'\b[A-Z]{4}\d{6}[H,M][A-Z]{5}[A-Z0-9]\d\b', '{{ curp }}'),

        # RFC (12-13 caracteres)
        (r'\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b', '{{ rfc }}'),
    ]

    for patron, remplazo in sustituciones:
        html = re.sub(patron, remplazo, html)

    return html


class Command(BaseCommand):
    help = 'Importa archivos .docx de la carpeta demandas/ como Machotes (plantillas HTML reutilizables)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reload',
            action='store_true',
            help='Re-importa todos los machotes (elimina los existentes)',
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Importa solo un archivo específico (nombre del archivo .docx)',
        )
        parser.add_argument(
            '--dir',
            type=str,
            default='demandas',
            help='Directorio donde están los archivos .docx (default: demandas)',
        )

    def handle(self, *args, **options):
        directorio = options['dir']
        solo_archivo = options['file']
        reload = options['reload']

        if not os.path.isdir(directorio):
            self.stderr.write(self.style.ERROR(f'El directorio "{directorio}" no existe.'))
            return

        if reload:
            Machote.objects.filter(archivo_origen__startswith=directorio).delete()
            self.stdout.write(self.style.WARNING('Machotes existentes eliminados.'))

        archivos = []
        if solo_archivo:
            ruta = os.path.join(directorio, solo_archivo)
            if os.path.isfile(ruta):
                archivos = [solo_archivo]
            else:
                self.stderr.write(self.style.ERROR(f'❌ Archivo "{solo_archivo}" no encontrado en {directorio}'))
                return
        else:
            archivos = sorted([
                f for f in os.listdir(directorio)
                if f.endswith('.docx') and not f.startswith('~')
            ])

        if not archivos:
            self.stdout.write(self.style.WARNING('No se encontraron archivos .docx.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Procesando {len(archivos)} archivo(s) desde "{directorio}/"...\n'))

        contador = 0
        for archivo in archivos:
            ruta = os.path.join(directorio, archivo)
            self.stdout.write(f'  {archivo}... ', ending='')

            try:
                # Clasificar el archivo
                clasificacion = clasificar_archivo(archivo)
                nombre_plantilla = extraer_nombre_plantilla(archivo)

                # Verificar si ya existe
                if Machote.objects.filter(archivo_origen=archivo).exists():
                    self.stdout.write(self.style.WARNING('Ya existe'))
                    continue

                # Extraer HTML del .docx
                html = docx_a_html(ruta)

                # Reemplazar datos específicos con marcadores
                html_con_marcadores = reemplazar_datos_con_marcadores(html)

                # Determinar ícono según categoría
                iconos = {
                    'demanda': '⚡',
                    'carta_finiquito': '📄',
                    'convenio': '🤝',
                    'solicitud': '📋',
                    'citatorio': '📬',
                    'otro': '📎',
                }

                # Crear el machote
                Machote.objects.create(
                    nombre=nombre_plantilla,
                    descripcion=f'Importado de: {archivo}',
                    categoria=clasificacion['categoria'],
                    tipo_despido=clasificacion['tipo_despido'],
                    jurisdiccion=clasificacion['jurisdiccion'],
                    contenido_html=html_con_marcadores,
                    icono=iconos.get(clasificacion['categoria'], '📄'),
                    activo=True,
                    orden=0,
                    archivo_origen=archivo,
                )

                self.stdout.write(self.style.SUCCESS('Importado'))
                contador += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error: {e}'))
                continue

        # Crear machotes por defecto si no hay ninguno
        if contador == 0 and Machote.objects.count() == 0:
            self.stdout.write('\n' + self.style.WARNING('No se importo ningun archivo. Creando machotes por defecto...'))
            self._crear_machotes_default()

        self.stdout.write('\n' + self.style.SUCCESS(f'{contador} machote(s) importado(s).'))
        self.stdout.write(f'   Total en BD: {Machote.objects.filter(activo=True).count()} machotes activos.')

    def _crear_machotes_default(self):
        """Crea machotes por defecto si no hay ninguno."""
        from django.utils import timezone

        hoy = timezone.now()
        mes = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
               'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'][hoy.month - 1]

        machotes_default = [
            {
                'nombre': 'Despido Injustificado - Federal',
                'descripcion': 'Plantilla general para demanda por despido injustificado ante tribunal federal.',
                'categoria': 'demanda',
                'tipo_despido': 'injustificado',
                'jurisdiccion': 'federal',
                'icono': '⚡',
                'orden': 1,
                'contenido_html': f"""<h2 style="text-align:center;color:#1F2937;">TRIBUNAL LABORAL COMPETENTE</h2>
<p style="text-align:center;color:#6B7280;">CIUDAD DE MÉXICO</p>
<hr style="border:none;border-top:1px solid #1D4ED8;width:70%;margin:10px auto;">

<h3 style="color:#1F2937;">—  A C T O R  —</h3>
<p><strong>{{ nombre_cliente }}</strong></p>
<p>Domicilio: {{ direccion_cliente }}</p>
<p>CURP: {{ curp_cliente }}</p>
<p>Teléfono: {{ telefono_cliente }}</p>

<h3 style="color:#1F2937;">—  D E M A N D A D O  —</h3>
<p><strong>{{ nombre_empresa }}</strong></p>
<p>Domicilio: {{ direccion_empresa }}</p>

<h3 style="color:#1F2937;">—  P R E S T A C I O N E S   R E C L A M A D A S  —</h3>
<p>Con fundamento en lo dispuesto por la Ley Federal del Trabajo, se reclaman las siguientes prestaciones:</p>
<ol>
<li>El pago de la Indemnización Constitucional de 90 días de salario, por concepto de despido injustificado, en términos del artículo 48 y 50 de la LFT.</li>
<li>El pago de Vacaciones Proporcionales correspondientes al último año de servicios, de conformidad con el artículo 76 de la LFT.</li>
<li>El pago de la Prima Vacacional del 25% sobre el monto de las vacaciones, conforme al artículo 80 de la LFT.</li>
<li>El pago del Aguinaldo Proporcional correspondiente, en términos del artículo 87 de la LFT.</li>
<li>El pago de la Prima de Antigüedad, conforme al artículo 162 de la LFT.</li>
<li>El pago de los Salarios Caídos que se sigan generando desde la fecha del despido hasta la fecha en que se dé cumplimiento al laudo.</li>
</ol>

<h3 style="color:#1F2937;">—  H E C H O S  —</h3>
<p><strong>PRIMERO.-</strong> El día {{ fecha_ingreso }}, el actor inició su relación laboral con el demandado {{ nombre_empresa }}, desempeñando el puesto de {{ puesto_trabajador }}, con un salario de {{ salario_mensual }} mensuales, pagaderos en la forma y términos convenidos.</p>

<p><strong>SEGUNDO.-</strong> El día {{ fecha_despido }}, el demandado dio por terminada la relación laboral de manera injustificada, violando en perjuicio del actor lo dispuesto por los artículos 46, 47 y 48 de la Ley Federal del Trabajo.</p>

<p><strong>TERCERO.-</strong> El actor agotó la instancia conciliatoria ante el Centro de Conciliación Laboral, según consta en el expediente número {{ folio_conciliacion }} de fecha {{ fecha_tramite }}, sin que se lograra acuerdo conciliatorio alguno, por lo que se expidió la constancia de no conciliación correspondiente.</p>

<p><strong>CUARTO.-</strong> A la fecha de presentación de esta demanda, el demandado no ha cubierto al actor el pago de las prestaciones laborales que se reclaman, a pesar de haber sido requerido para ello.</p>

<h3 style="color:#1F2937;">—  F U N D A M E N T O S   D E   D E R E C H O  —</h3>
<p>• Artículo 84 LFT — Salario integrado</p>
<p>• Artículo 87 LFT — Aguinaldo anual (15 días mínimo)</p>
<p>• Artículo 76 LFT — Vacaciones</p>
<p>• Artículo 79 LFT — Prima vacacional (mínimo 25%)</p>
<p>• Artículo 80 LFT — Pago de prima vacacional</p>
<p>• Artículo 46 LFT — Terminación de la relación laboral</p>
<p>• Artículo 47 LFT — Causas de rescisión sin responsabilidad</p>
<p>• Artículo 48 LFT — Indemnización por despido injustificado</p>
<p>• Artículo 50 LFT — Indemnización de 3 meses</p>
<p>• Artículo 162 LFT — Prima de antigüedad</p>
<p>• Artículo 518 LFT — Procedimiento ordinario laboral</p>

<h3 style="color:#1F2937;">—  P U N T O S   P E T I T O R I O S  —</h3>
<p><strong>PRIMERO.-</strong> Se declare que existió una relación laboral entre el actor y el demandado.</p>
<p><strong>SEGUNDO.-</strong> Se condene al demandado al pago de {{ monto_total }} por concepto de las prestaciones laborales detalladas en el cuerpo de esta demanda.</p>
<p><strong>TERCERO.-</strong> Se ordene el pago de los salarios caídos que se sigan generando hasta la fecha en que se cumpla la sentencia.</p>
<p><strong>CUARTO.-</strong> Se condene al demandado al pago de los gastos y costas que se originen con motivo del presente juicio.</p>

<h3 style="color:#1F2937;">—  F I R M A  —</h3>
<p>Presentado en la Ciudad de México, a los {{ hoy }}.</p>
<br>
<p style="text-align:center;">________________________________________</p>
<p style="text-align:center;font-weight:bold;font-size:14px;">{{ nombre_cliente }}</p>
<p style="text-align:center;color:#6B7280;">Actor</p>"""
            },
            {
                'nombre': 'Despido Injustificado - Baja California',
                'descripcion': 'Plantilla para demanda por despido injustificado ante el Tribunal Laboral del Estado de Baja California.',
                'categoria': 'demanda',
                'tipo_despido': 'injustificado',
                'jurisdiccion': 'estatal',
                'icono': '⚖️',
                'orden': 2,
                'contenido_html': f"""<h2 style="text-align:center;color:#1F2937;">TRIBUNAL LABORAL DEL ESTADO DE BAJA CALIFORNIA</h2>
<p style="text-align:center;color:#6B7280;">EN TIJUANA, BAJA CALIFORNIA</p>
<hr style="border:none;border-top:1px solid #1D4ED8;width:70%;margin:10px auto;">

<h3 style="color:#1F2937;">—  A C T O R  —</h3>
<p><strong>{{ nombre_cliente }}</strong></p>
<p>Domicilio: {{ direccion_cliente }}</p>
<p>CURP: {{ curp_cliente }}</p>

<h3 style="color:#1F2937;">—  D E M A N D A D O  —</h3>
<p><strong>{{ nombre_empresa }}</strong></p>
<p>Domicilio: {{ direccion_empresa }}</p>

<h3 style="color:#1F2937;">—  P R E S T A C I O N E S   R E C L A M A D A S  —</h3>
<ol>
<li>La indemnización constitucional por despido injustificado de 90 días de salario, conforme al artículo 48 y 50 de la LFT.</li>
<li>El pago de vacaciones proporcionales y prima vacacional del 25%.</li>
<li>El pago de aguinaldo proporcional.</li>
<li>El pago de prima de antigüedad.</li>
<li>El pago de salarios caídos desde la fecha del despido hasta la total solución del conflicto.</li>
</ol>

<h3 style="color:#1F2937;">—  H E C H O S  —</h3>
<p><strong>PRIMERO.-</strong> Con fecha {{ fecha_ingreso }}, el actor inició su relación de trabajo con el demandado {{ nombre_empresa }}, desempeñando el puesto de {{ puesto_trabajador }}, con un salario de {{ salario_mensual }} mensuales.</p>

<p><strong>SEGUNDO.-</strong> El día {{ fecha_despido }}, el C. {{ nombre_representante }}, en su carácter de {{ cargo_representante }} de la empresa demandada, comunicó al actor que quedaba despedido de su empleo, sin que mediara causa justificada para ello.</p>

<p><strong>TERCERO.-</strong> El actor agotó la instancia conciliatoria ante el Centro de Conciliación Laboral del Estado de Baja California, obteniendo constancia de no conciliación de fecha {{ fecha_tramite }}, con número de folio {{ folio_conciliacion }}.</p>

<p><strong>CUARTO.-</strong> El demandado no ha dado cumplimiento al pago de las prestaciones que por ley le corresponden al actor.</p>

<h3 style="color:#1F2937;">—  F U N D A M E N T O S   D E   D E R E C H O  —</h3>
<p>• Artículo 123 Apartado A fracción XXII de la Constitución Política de los Estados Unidos Mexicanos.</p>
<p>• Artículos 46, 47, 48, 50, 76, 79, 80, 84, 87, 162 y 518 de la Ley Federal del Trabajo.</p>

<h3 style="color:#1F2937;">—  P U N T O S   P E T I T O R I O S  —</h3>
<p><strong>PRIMERO.-</strong> Se declare procedente la acción ejercitada por el actor.</p>
<p><strong>SEGUNDO.-</strong> Se condene al demandado al pago de las prestaciones reclamadas.</p>
<p><strong>TERCERO.-</strong> Se condene al demandado al pago de los salarios caídos.</p>
<p><strong>CUARTO.-</strong> Se condene al demandado al pago de gastos y costas del presente juicio.</p>

<h3 style="color:#1F2937;">—  F I R M A  —</h3>
<p>Presentado en Tijuana, Baja California, a los {{ hoy }}.</p>
<br>
<p style="text-align:center;">________________________________________</p>
<p style="text-align:center;font-weight:bold;font-size:14px;">{{ nombre_cliente }}</p>
<p style="text-align:center;color:#6B7280;">Actor</p>"""
            },
            {
                'nombre': 'Rescisión de Relación Laboral',
                'descripcion': 'Plantilla para demanda por rescisión de la relación laboral imputable al patrón (Art. 51 LFT).',
                'categoria': 'demanda',
                'tipo_despido': 'rescision',
                'jurisdiccion': 'federal',
                'icono': '🛡️',
                'orden': 3,
                'contenido_html': """<h2 style="text-align:center;color:#1F2937;">TRIBUNAL LABORAL COMPETENTE</h2>
<p style="text-align:center;color:#6B7280;">CIUDAD DE MÉXICO</p>
<hr style="border:none;border-top:1px solid #1D4ED8;width:70%;margin:10px auto;">

<h3 style="color:#1F2937;">—  A C T O R  —</h3>
<p><strong>{{ nombre_cliente }}</strong></p>

<h3 style="color:#1F2937;">—  D E M A N D A D O  —</h3>
<p><strong>{{ nombre_empresa }}</strong></p>

<h3 style="color:#1F2937;">—  P R E S T A C I O N E S   R E C L A M A D A S  —</h3>
<ol>
<li>La indemnización constitucional de 90 días de salario, en términos del artículo 50 de la LFT.</li>
<li>El pago de vacaciones proporcionales y prima vacacional.</li>
<li>El pago de aguinaldo proporcional.</li>
<li>El pago de prima de antigüedad.</li>
<li>El pago de salarios caídos.</li>
</ol>

<h3 style="color:#1F2937;">—  H E C H O S  —</h3>
<p><strong>PRIMERO.-</strong> Con fecha {{ fecha_ingreso }}, el actor inició su relación laboral con el demandado {{ nombre_empresa }}, desempeñando el puesto de {{ puesto_trabajador }}, con un salario de {{ salario_mensual }} mensuales.</p>

<p><strong>SEGUNDO.-</strong> Durante la relación laboral, el demandado incurrió en conductas que dieron lugar a la rescisión de la relación laboral por causas imputables al patrón, en términos del artículo 51 de la Ley Federal del Trabajo.</p>

<p><strong>TERCERO.-</strong> En virtud de lo anterior, el actor se vio en la necesidad de dar por terminada la relación laboral, notificando al demandado las causas de rescisión.</p>

<p><strong>CUARTO.-</strong> El actor agotó la instancia conciliatoria sin haberse logrado acuerdo alguno.</p>

<h3 style="color:#1F2937;">—  F U N D A M E N T O S   D E   D E R E C H O  —</h3>
<p>• Artículo 51 LFT — Causas de rescisión imputables al patrón</p>
<p>• Artículo 52 LFT — Aviso de rescisión</p>
<p>• Artículo 48 y 50 LFT — Indemnización</p>
<p>• Artículo 162 LFT — Prima de antigüedad</p>

<h3 style="color:#1F2937;">—  P U N T O S   P E T I T O R I O S  —</h3>
<p><strong>PRIMERO.-</strong> Se declare que la relación laboral terminó por causas imputables al patrón.</p>
<p><strong>SEGUNDO.-</strong> Se condene al demandado al pago de la totalidad de las prestaciones reclamadas.</p>

<h3 style="color:#1F2937;">—  F I R M A  —</h3>
<p>Presentado en la Ciudad de México, a los {{ hoy }}.</p>
<br>
<p style="text-align:center;">________________________________________</p>
<p style="text-align:center;font-weight:bold;font-size:14px;">{{ nombre_cliente }}</p>
<p style="text-align:center;color:#6B7280;">Actor</p>"""
            },
        ]

        for datos in machotes_default:
            Machote.objects.get_or_create(
                nombre=datos['nombre'],
                defaults=datos
            )
            self.stdout.write(f'  Creado: {datos["nombre"]}')
