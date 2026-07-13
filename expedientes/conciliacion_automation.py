"""
Conciliación B.C. — Automatización del Formulario Web (v2)
===========================================================

FLUJO REAL DEL SITIO (app.conciliacionbc.gob.mx):
    1. Aviso de Privacidad → Aceptar
    2. Industria → "ninguna de las anteriores" → "Validar y Continuar"
    3. Fecha conflicto + objeto → "Validar y Continuar"
    4. Tab "Solicitante" → "Agregar solicitante" → llenar campos → "Guardar" → "Validar y Continuar"
    5. Tab "Citado" → "Agregar citado" → llenar campos → "Guardar" → "Validar y Continuar"
    6. Tab "Descripción" → llenar textarea → "Aceptar"
    7. Tab "Resumen" → "Enviar solicitud" → confirmar → Descargar acuse PDF

Diferencias con v1 (código anterior):
    - El sitio NO tiene cuestionario previo (Soy empleado, despedieron, orientacion, etc.)
    - Los campos NO están dentro de modales Bootstrap — están en la página normal
    - Navegación por tabs/wizard, no por pasos secuenciales con botones
    - Los contactos usan contactos[1], contactos[2], contactos[3] (no contactos[0][telefono])
"""
import logging
import re
import tempfile
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class ResultadoConciliacion:
    """Resultado del envío automatizado al portal de conciliación."""
    success: bool = False
    folio: str = ''
    pdf_path: str = ''
    error: str = ''
    detalle: str = ''
    screenshots: list = field(default_factory=list)


# ─── URLs del sitio ──────────────────────────────────────────────────────

URL_BASE = 'https://app.conciliacionbc.gob.mx'
URL_SOLICITUD = f'{URL_BASE}/solicitudes/create-public?solicitud=1'


# ══════════════════════════════════════════════════════════════════════════
#  Helpers de navegación - Usan Playwright nativo siempre que sea posible
# ══════════════════════════════════════════════════════════════════════════


def _btn_click(page, texto_contiene, timeout=10000):
    """Busca un botón cuyo texto contenga el string dado y hace clic."""
    try:
        btn = page.locator('button, a').filter(has_text=re.compile(re.escape(texto_contiene), re.IGNORECASE)).first
        if btn.count():
            btn.click(timeout=timeout)
            return True
    except Exception:
        pass
    # Fallback JS
    try:
        return page.evaluate(f"""(txt) => {{
            for (const el of document.querySelectorAll('button, a')) {{
                if (el.textContent.trim().toLowerCase().includes(txt.toLowerCase()) && el.offsetParent !== null) {{
                    el.click();
                    el.dispatchEvent(new Event('click', {{bubbles: true}}));
                    return true;
                }}
            }}
            return false;
        }}""", texto_contiene)
    except Exception:
        return False


def _fill_input(page, name, valor):
    """Llena un input usando JS directamente.
    
    Usamos JS siempre porque:
    - Playwright fill() nativo timeout de 30s cuando el campo no es visible
    - El sitio tiene campos que aparecen/desaparecen dinámicamente
    - JS es más rápido y confiable para este sitio
    """
    if not valor:
        return False
    try:
        return page.evaluate("""(args) => {
            const [name, valor] = args;
            const el = document.querySelector(`[name="${name}"]`);
            if (el) {
                el.focus();
                el.value = valor;
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                el.dispatchEvent(new Event('blur'));
                return true;
            }
            return false;
        }""", [name, str(valor)])
    except Exception:
        pass
    return False


def _select_option(page, name, valor):
    """Selecciona una opción en un select usando JS directamente."""
    if not valor:
        return False
    try:
        return page.evaluate("""(args) => {
            const [name, valor] = args;
            const el = document.querySelector(`[name="${name}"]`);
            if (el && el.tagName === 'SELECT') {
                el.value = valor;
                el.dispatchEvent(new Event('change', {bubbles: true}));
                return true;
            }
            return false;
        }""", [name, str(valor)])
    except Exception:
        pass
    return False


def _click_radio(page, name, value):
    """Selecciona un radio button por name y value.
    Usa JS directamente porque Bootstrap custom radios tienen labels que
    interceptan los clicks nativos de Playwright."""
    return page.evaluate("""(args) => {
        const [name, value] = args;
        const r = document.querySelector(`input[name="${name}"][value="${value}"]`);
        if (r) {
            r.click();
            r.dispatchEvent(new Event('change', {bubbles: true}));
            return true;
        }
        return false;
    }""", [name, value])


def _navigate_wizard_tab(page, texto_contiene):
    """Navega a un tab del wizard por su texto."""
    try:
        locator = page.locator('.wizard-step a, .nav-link, .step-title').filter(
            has_text=re.compile(re.escape(texto_contiene), re.IGNORECASE)
        ).first
        if locator.count():
            locator.click()
            page.wait_for_timeout(1500)
            return True
    except Exception:
        pass
    return page.evaluate(f"""(kw) => {{
        for (const el of document.querySelectorAll('.wizard-step a, .nav-link, .step-title, a[class*="step"]')) {{
            const txt = el.textContent.trim().toLowerCase();
            if (txt.includes(kw.toLowerCase())) {{
                el.click();
                el.dispatchEvent(new Event('click', {{bubbles: true}}));
                return true;
            }}
        }}
        return false;
    }}""", texto_contiene)


def _cerrar_modales(page):
    """Cierra cualquier modal/overlay que esté abierto."""
    return page.evaluate("""() => {
        let count = 0;
        // Cerrar SweetAlert primero
        const swal = document.querySelector('.swal-overlay--show-modal, .swal-overlay');
        if (swal) {
            // Click en botón OK del SweetAlert
            const okBtn = swal.querySelector('.swal-button--confirm, .swal-button, button');
            if (okBtn) { okBtn.click(); count++; }
            swal.style.display = 'none';
            swal.classList.remove('swal-overlay--show-modal');
            count++;
        }
        document.querySelectorAll('.swal-overlay, .swal-modal').forEach(el => {
            el.style.display = 'none';
            count++;
        });
        // Clic en botones "Entendido", "Cerrar", etc.
        for (const btn of document.querySelectorAll('button, a')) {
            const txt = btn.textContent.trim().toLowerCase();
            if (['entendido', 'cerrar', 'close', 'aceptar', 'ok', 'continuar', 'si, enviar'].some(k => txt.includes(k))) {
                if (btn.offsetParent !== null) {
                    btn.click();
                    count++;
                    break;
                }
            }
        }
        // Cerrar modales de Bootstrap
        document.querySelectorAll('.modal.show, .modal.fade.show').forEach(m => {
            m.classList.remove('show');
            m.style.display = 'none';
            count++;
        });
        document.querySelectorAll('.modal-backdrop').forEach(b => {
            b.remove();
            count++;
        });
        document.body.classList.remove('modal-open');
        document.body.style.paddingRight = '';
        return count;
    }""")


def _click_validar_continuar(page):
    """Hace clic en el botón 'Validar y Continuar'."""
    try:
        btn = page.get_by_role('button').filter(has_text=re.compile(r'validar', re.IGNORECASE)).and_(
            page.get_by_role('button').filter(has_text=re.compile(r'continuar', re.IGNORECASE))
        ).first
        if btn.count():
            btn.click(timeout=10000)
            return True
    except Exception:
        pass
    # Fallback: buscar botón que contenga ambos textos
    return page.evaluate("""() => {
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim().toLowerCase();
            if (t.includes('validar') && t.includes('continuar')) {
                btn.click();
                btn.dispatchEvent(new Event('click', {bubbles: true}));
                return true;
            }
        }
        return false;
    }""")


# ══════════════════════════════════════════════════════════════════════════
#  Llenado de datos del solicitante y citado
# ══════════════════════════════════════════════════════════════════════════


# ─── Mapeo de valores del modelo a IDs del portal BC ───────────────────

GENERO_PORTAL_IDS = {
    'masculino': '1',
    'femenino': '2',
}

PERIODICIDAD_PORTAL_IDS = {
    'diario': '1',      # Diario
    'mensual': '2',      # Mensual
    'quincenal': '3',    # Quincenal
    'semanal': '4',      # Semanal
}

JORNADA_PORTAL_IDS = {
    'diurna': '1',       # DIURNA
    'nocturna': '2',     # NOCTURNA
    'mixta': '3',        # MIXTA
}

TIPO_PERSONA_PORTAL_IDS = {
    'fisica': '1',       # Persona Física
    'moral': '2',        # Persona Moral
}


def _llenar_solicitante(page, cliente, fecha_nac_str, fecha_ing_str, fecha_sal_str):
    """Llena los campos del solicitante (trabajador)."""
    nombre_parts = (cliente.nombre or '').split()
    curp = cliente.curp or 'XAXX010101000'

    # Datos personales
    _fill_input(page, 'solicitante[curp]', curp)
    _fill_input(page, 'solicitante[nombre]', nombre_parts[0] if nombre_parts else 'Juan')
    _fill_input(page, 'solicitante[primer_apellido]', nombre_parts[1] if len(nombre_parts) > 1 else 'Perez')
    _fill_input(page, 'solicitante[segundo_apellido]', nombre_parts[2] if len(nombre_parts) > 2 else 'Lopez')
    _fill_input(page, 'solicitante[fecha_nacimiento]', fecha_nac_str)

    # Género y nacionalidad
    genero_id = GENERO_PORTAL_IDS.get(cliente.genero, '1')
    _select_option(page, 'solicitante[genero_id]', genero_id)
    _select_option(page, 'solicitante[nacionalidad_id]', '1')   # MEXICANA (siempre)

    # Contactos (teléfono) — el sitio usa contactos[1], contactos[2], contactos[3]
    _fill_input(page, 'contactos[1]', cliente.telefono or '6641234567')

    # Domicilio
    _select_option(page, 'domicilio[estado_id]', '02')              # Baja California
    _select_option(page, 'domicilio[tipo_vialidad_id]', '5')        # CALLE
    _fill_input(page, 'domicilio[vialidad]', cliente.direccion_calle or 'Av Principal')
    _fill_input(page, 'domicilio[num_ext]', cliente.direccion_numero or '123')
    _fill_input(page, 'domicilio[cp]', cliente.direccion_cp or '22000')
    _select_option(page, 'domicilio[asentamiento]', cliente.direccion_colonia or 'Centro')
    _select_option(page, 'municipio', 'Tijuana')

    # Datos laborales
    periodicidad_id = PERIODICIDAD_PORTAL_IDS.get(cliente.periodo_pago, '2')
    horas = str(cliente.horas_semanales or 40)
    jornada_id = JORNADA_PORTAL_IDS.get(cliente.jornada, '1')

    _fill_input(page, 'dato_laboral[puesto]', cliente.puesto or 'Trabajador')
    _fill_input(page, 'dato_laboral[remuneracion]', str(float(cliente.salario or 10000)))
    _select_option(page, 'dato_laboral[periodicidad_id]', periodicidad_id)
    _fill_input(page, 'dato_laboral[horas_semanales]', horas)
    _fill_input(page, 'dato_laboral[fecha_ingreso]', fecha_ing_str)
    _fill_input(page, 'dato_laboral[fecha_salida]', fecha_sal_str)
    _select_option(page, 'dato_laboral[jornada_id]', jornada_id)

    page.wait_for_timeout(1000)

    # Click "Guardar" para cerrar el panel del solicitante
    _btn_click(page, 'guardar', timeout=5000)


def _llenar_citado(page, cliente):
    """Llena los campos del citado (empresa/patrón)."""
    empresa_nombre = cliente.empresa_razon_social or cliente.empresa or 'Empresa SA de CV'
    nombre_parts = empresa_nombre.split()

    # Tipo persona: desde el modelo (Física o Moral)
    tipo_persona_id = TIPO_PERSONA_PORTAL_IDS.get(cliente.tipo_persona_citado, '1')
    _click_radio(page, 'solicitado[tipo_persona_id]', tipo_persona_id)
    page.wait_for_timeout(500)

    # Datos del citado
    _fill_input(page, 'solicitado[nombre]', nombre_parts[0] if nombre_parts else 'Empresa')
    _fill_input(page, 'solicitado[primer_apellido]', nombre_parts[1] if len(nombre_parts) > 1 else 'SA')
    _fill_input(page, 'solicitado[segundo_apellido]',
                'de CV' if len(nombre_parts) <= 2 else ' '.join(nombre_parts[2:]))
    _select_option(page, 'solicitado[genero_id]', '1')             # MASCULINO
    _select_option(page, 'solicitado[nacionalidad_id]', '1')       # MEXICANA

    # Domicilio del citado
    _select_option(page, 'domicilio[estado_id]', '02')
    _select_option(page, 'domicilio[tipo_vialidad_id]', '5')
    _fill_input(page, 'domicilio[vialidad]', cliente.empresa_calle or cliente.direccion_calle or 'Av Principal')
    _fill_input(page, 'domicilio[num_ext]', cliente.empresa_numero or cliente.direccion_numero or '123')
    _fill_input(page, 'domicilio[cp]', cliente.empresa_cp or cliente.direccion_cp or '22000')
    _select_option(page, 'domicilio[asentamiento]', cliente.empresa_colonia or cliente.direccion_colonia or 'Centro')
    _select_option(page, 'municipio', 'Tijuana')

    # Teléfono de contacto
    _fill_input(page, 'contactos[1]', cliente.empresa_telefono or cliente.telefono or '6641234567')

    page.wait_for_timeout(1000)

    # Click "Guardar" para cerrar el panel del citado
    _btn_click(page, 'guardar', timeout=5000)


# ══════════════════════════════════════════════════════════════════════════
#  Automatización Principal (flujo real del sitio)
# ══════════════════════════════════════════════════════════════════════════


def enviar_a_conciliacion(expediente, headless=True, download_dir=None) -> ResultadoConciliacion:
    """
    Automatiza el envío de la solicitud al portal de conciliación de Baja California.

    Args:
        expediente: Instancia del modelo Expediente con cliente relacionado.
        headless: Si True, corre el navegador sin interfaz gráfica.
        download_dir: Directorio para guardar screenshots y PDFs.

    Returns:
        ResultadoConciliacion con folio y ruta del PDF si tuvo éxito.
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

    resultado = ResultadoConciliacion(success=False)
    cliente = expediente.cliente

    if not download_dir:
        download_dir = tempfile.mkdtemp(prefix='conciliacion_')
    else:
        Path(download_dir).mkdir(parents=True, exist_ok=True)

    # Variables de fechas
    fecha_conflicto = cliente.fecha_salida or expediente.fecha_tramite or date.today()
    fecha_nac = cliente.fecha_nacimiento or (cliente.fecha_ingreso or date.today()) - timedelta(days=365 * 30)
    fecha_ing = cliente.fecha_ingreso or date.today().replace(year=date.today().year - 2)
    fecha_sal = cliente.fecha_salida or date.today()

    fmt_fecha = lambda f: f.strftime('%d/%m/%Y')

    pdf_descargado = None

    try:
        with sync_playwright() as p:
            # ── En producción (Railway/Docker) siempre forzar headless ──
            # El modo "debug" (headless=False) requiere un servidor X,
            # que no está disponible en contenedores Docker.
            import os as _os
            _force_headless = _os.environ.get('FORCE_HEADLESS', 'true').lower() == 'true'
            _actual_headless = headless if not _force_headless else True

            browser = p.chromium.launch(
                headless=_actual_headless,
                slow_mo=300 if not _actual_headless else 100,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
                timeout=20000,
            )
            context = browser.new_context(
                viewport={'width': 1280, 'height': 900},
                accept_downloads=True,
                locale='es-MX',
            )

            # Capturar descargas de PDF
            def on_download(download):
                nonlocal pdf_descargado
                dest = str(Path(download_dir) / download.suggested_filename)
                download.save_as(dest)
                pdf_descargado = dest
                logger.info('  PDF descargado: %s', dest)

            context.on('download', on_download)

            page = context.new_page()

            def screenshot(name):
                path = str(Path(download_dir) / f'{name}.png')
                try:
                    page.screenshot(path=path, full_page=True)
                    resultado.screenshots.append(path)
                except Exception:
                    pass

            def checkpoint(name):
                screenshot(name)
                try:
                    texto = page.evaluate("() => document.body.innerText")
                    logger.info('  [%s] Texto: %s...', name, texto[:200].replace('\n', ' | '))
                    return texto
                except Exception:
                    return ''

            # ════════════════════════════════════════════════════════════════
            #  FASE 0: Cargar página
            # ════════════════════════════════════════════════════════════════
            logger.info('[Carga] Navegando a %s', URL_SOLICITUD)
            try:
                page.goto(URL_SOLICITUD, wait_until='networkidle', timeout=30000)
            except PwTimeout:
                page.goto(URL_SOLICITUD, timeout=30000)
            page.wait_for_timeout(3000)
            checkpoint('00_inicio')

            # ════════════════════════════════════════════════════════════════
            #  FASE 1: Aviso de Privacidad
            # ════════════════════════════════════════════════════════════════
            logger.info('[1] Aceptando aviso de privacidad...')

            # Seleccionar radio "Acepto" (radioAviso = '1')
            _click_radio(page, 'radioAviso', '1')
            page.wait_for_timeout(500)

            # Click "Aceptar"
            _btn_click(page, 'Aceptar')
            page.wait_for_timeout(2000)

            # Cerrar modales que aparezcan
            _cerrar_modales(page)
            page.wait_for_timeout(1000)
            checkpoint('01_aviso_aceptado')

            # ════════════════════════════════════════════════════════════════
            #  FASE 2: Industria
            # ════════════════════════════════════════════════════════════════
            logger.info('[2] Seleccionando industria...')

            # Seleccionar "Ninguna de las anteriores" (industria = 28)
            _click_radio(page, 'industria', '28')
            page.wait_for_timeout(1500)

            # Cerrar modal informativo que pueda aparecer
            _cerrar_modales(page)
            page.wait_for_timeout(500)

            # Click "Validar y Continuar"
            _click_validar_continuar(page)
            page.wait_for_timeout(3000)

            # Cerrar modales
            _cerrar_modales(page)
            page.wait_for_timeout(1000)
            checkpoint('02_industria')

            # ════════════════════════════════════════════════════════════════
            #  FASE 3: Fecha de conflicto y objeto de la solicitud
            # ════════════════════════════════════════════════════════════════
            logger.info('[3] Llenando fecha y objeto...')

            # Llenar fecha de conflicto
            _fill_input(page, 'solicitud[fecha_conflicto]', fmt_fecha(fecha_conflicto))
            page.wait_for_timeout(500)

            # Seleccionar objeto (despido = '1')
            _select_option(page, 'solicitud[objeto_id]', '1')
            page.wait_for_timeout(500)

            # Click "Validar y Continuar"
            _click_validar_continuar(page)
            page.wait_for_timeout(3000)
            checkpoint('03_fecha_objeto')

            # ════════════════════════════════════════════════════════════════
            #  FASE 4: Solicitante (Trabajador)
            # ════════════════════════════════════════════════════════════════
            logger.info('[4] Llenando datos del solicitante...')

            # Navegar al tab "Solicitante"
            _navigate_wizard_tab(page, 'solicitante')
            page.wait_for_timeout(1500)

            # Click "Agregar solicitante"
            _btn_click(page, 'agregar solicitante')
            page.wait_for_timeout(3000)

            # Llenar campos del solicitante
            _llenar_solicitante(page, cliente,
                                fmt_fecha(fecha_nac),
                                fmt_fecha(fecha_ing),
                                fmt_fecha(fecha_sal))
            page.wait_for_timeout(2000)
            checkpoint('04_solicitante')

            # Click "Validar y Continuar"
            _click_validar_continuar(page)
            page.wait_for_timeout(3000)
            checkpoint('04_solicitante_validado')

            # ════════════════════════════════════════════════════════════════
            #  FASE 5: Citado (Empresa/Patrón)
            # ════════════════════════════════════════════════════════════════
            logger.info('[5] Llenando datos del citado...')

            # Navegar al tab "Citado"
            _navigate_wizard_tab(page, 'citado')
            page.wait_for_timeout(1500)

            # Click "Agregar citado"
            _btn_click(page, 'agregar citado')
            page.wait_for_timeout(3000)

            # Llenar campos del citado
            _llenar_citado(page, cliente)
            page.wait_for_timeout(2000)
            checkpoint('05_citado')

            # Click "Validar y Continuar"
            _click_validar_continuar(page)
            page.wait_for_timeout(3000)
            checkpoint('05_citado_validado')

            # ════════════════════════════════════════════════════════════════
            #  FASE 6: Descripción de los hechos
            # ════════════════════════════════════════════════════════════════
            logger.info('[6] Llenando descripción de los hechos...')

            # Navegar al tab "Descripción"
            _navigate_wizard_tab(page, 'descripci')
            page.wait_for_timeout(1500)

            # Construir texto de descripción
            hechos = [
                f'El día {fmt_fecha(fecha_conflicto)} fui despedido injustificadamente'
            ]
            if cliente.empresa:
                hechos[0] += f' de mi empleo en {cliente.empresa}'
            if cliente.puesto:
                hechos.append(f'Donde laboraba como {cliente.puesto}.' )
            else:
                hechos[0] += '.'
            if cliente.salario:
                hechos.append(f'Mi salario mensual era de ${cliente.salario:.2f}.' )
            if cliente.fecha_ingreso:
                hechos.append(f'Ingresé a laborar el {fmt_fecha(cliente.fecha_ingreso)}.')
            hechos.append('Solicito el pago de mis prestaciones de ley.')

            texto_hechos = ' '.join(hechos)

            # Cerrar cualquier modal/SweetAlert que esté bloqueando
            _cerrar_modales(page)
            page.wait_for_timeout(500)

            # Llenar textarea con JS (evita interceptación de SweetAlert/modales)
            page.evaluate("""(texto) => {
                const ta = document.querySelector('textarea');
                if (ta) {
                    ta.focus();
                    ta.value = texto;
                    ta.dispatchEvent(new Event('input', {bubbles: true}));
                    ta.dispatchEvent(new Event('change', {bubbles: true}));
                }
            }""", texto_hechos)
            page.wait_for_timeout(500)

            # Click "Aceptar"
            _btn_click(page, 'aceptar')
            page.wait_for_timeout(3000)
            checkpoint('06_descripcion')

            # ════════════════════════════════════════════════════════════════
            #  FASE 7: Resumen y Envío
            # ════════════════════════════════════════════════════════════════
            logger.info('[7] Navegando a resumen y enviando...')

            # Navegar al tab "Resumen"
            _navigate_wizard_tab(page, 'resumen')
            page.wait_for_timeout(2000)

            # Verificar errores antes de enviar
            errores = page.evaluate("""() => {
                const errs = [];
                document.querySelectorAll('.text-danger, .error, .invalid-feedback, .is-invalid, .help-block').forEach(el => {
                    const txt = el.textContent.trim();
                    if (txt) {
                        let input = el.closest('[class*="col"], div')?.querySelector('input, select, textarea');
                        errs.push({ msg: txt.substring(0, 60), name: input?.name || input?.id || '' });
                    }
                });
                return errs;
            }""")
            if errores:
                logger.warning('  Errores detectados antes de enviar: %s', errores)
                # Si hay errores, intentar navegar de vuelta a corregir
                for err in errores[:3]:
                    logger.warning('  Error: %s (campo: %s)', err['msg'], err['name'])

            # Click "Enviar solicitud"
            logger.info('[7a] Click en Enviar solicitud...')
            _btn_click(page, 'enviar solicitud')
            page.wait_for_timeout(4000)

            # Click "Enviar" (confirmación)
            logger.info('[7b] Confirmando envío...')
            _btn_click(page, 'enviar')
            page.wait_for_timeout(5000)

            # Cerrar modal de éxito
            _cerrar_modales(page)
            page.wait_for_timeout(1000)
            checkpoint('07_enviado')

            # ════════════════════════════════════════════════════════════════
            #  FASE 8: Descargar acuse / PDF
            # ════════════════════════════════════════════════════════════════
            logger.info('[8] Descargando acuse...')

            # Click "Descargar acuse" o similar
            _btn_click(page, 'descargar')
            page.wait_for_timeout(3000)

            _btn_click(page, 'acuse')
            page.wait_for_timeout(3000)

            # Esperar a que termine la descarga
            page.wait_for_timeout(3000)

            # ── Extraer folio del PDF descargado ──────────────────────
            logger.info('[Folio] Buscando PDF descargado...')
            if pdf_descargado:
                pdf_path = Path(pdf_descargado)
                resultado.pdf_path = str(pdf_path)
                nombre_pdf = pdf_path.stem
                logger.info('  Nombre PDF: %s', nombre_pdf)

                folio_match = re.search(r'(CCL[/\\-][\\w/-]+|[\\d]{4,}-[\\d]+|[\\w-]+folio[\\w-]*)',
                                        nombre_pdf, re.IGNORECASE)
                if folio_match:
                    resultado.folio = folio_match.group(1)

                # Si no está en el nombre, buscar en el contenido del PDF
                if not resultado.folio:
                    try:
                        with open(pdf_descargado, 'rb') as f:
                            contenido = f.read()
                        texto_pdf = contenido.decode('latin-1', errors='ignore')
                        folio_match = re.search(
                            r'(CCL[:\\s]*[/\\d\\-]+|FOLIO[:\\s]*[\\w/-]+)',
                            texto_pdf, re.IGNORECASE
                        )
                        if folio_match:
                            resultado.folio = folio_match.group(1).strip()
                    except Exception as e:
                        logger.warning('  No se pudo leer PDF: %s', e)

                resultado.success = True
                resultado.detalle = f'Solicitud enviada. Folio: {resultado.folio or "N/A"}'
                logger.info('  Éxito! Folio=%s PDF=%s', resultado.folio, pdf_descargado)
            else:
                logger.warning('  No se descargó ningún PDF')
                texto_final = checkpoint('08_final')

                # Buscar enlace de descarga en la página
                doc_url = page.evaluate("""() => {
                    const links = document.querySelectorAll('a[href*="getFile"], a[href*="documento"], a[href*="folio"]');
                    for (const link of links) {
                        if (link.href) return link.href;
                    }
                    return '';
                }""")
                if doc_url:
                    resultado.detalle = f'Solicitud enviada. URL documento: {doc_url}'
                    folio_match = re.search(r'getFile/([\\w-]+)', doc_url)
                    if folio_match:
                        resultado.folio = folio_match.group(1)
                        resultado.success = True
                else:
                    resultado.error = 'No se pudo descargar el acuse ni obtener folio'
                    resultado.detalle = f'URL final: {page.url}'

            browser.close()

    except Exception as e:
        logger.exception('Error en la automatización de conciliación')
        resultado.error = f'{type(e).__name__}: {e}'

    return resultado


# ══════════════════════════════════════════════════════════════════════════
#  Función de alto nivel (guarda resultado en BD)
# ══════════════════════════════════════════════════════════════════════════


def enviar_y_guardar(expediente, usuario=None, headless=True) -> ResultadoConciliacion:
    """Envía la solicitud al portal y guarda el resultado en el expediente."""
    from django.core.files import File

    resultado = enviar_a_conciliacion(expediente, headless=headless)

    if resultado.success:
        expediente.folio = resultado.folio or expediente.folio
        expediente.fecha_tramite = timezone.now().date()
        expediente.save()

        if resultado.pdf_path and Path(resultado.pdf_path).exists():
            from .models import Documento
            doc = Documento(
                expediente=expediente,
                descripcion=f'Solicitud de Conciliación (Folio: {resultado.folio or "N/A"})',
                tipo='citatorio',
                subido_por=usuario or getattr(expediente, 'asesor', None),
            )
            with open(resultado.pdf_path, 'rb') as f:
                doc.archivo.save(
                    f'solicitud_conciliacion_{expediente.numero}.pdf',
                    File(f),
                    save=True,
                )

        if usuario:
            from .signals import registrar_movimiento
            registrar_movimiento(
                expediente=expediente,
                usuario=usuario,
                accion='actualizacion',
                detalle=f'Solicitud de conciliación enviada al portal. Folio: {resultado.folio or "N/A"}'
            )

    return resultado
