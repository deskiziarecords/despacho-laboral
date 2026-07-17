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
import os
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
    try:
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
    except Exception:
        return False


def _navigate_wizard_tab(page, texto_contiene):
    """Navega a un tab del wizard por su texto."""
    try:
        locator = page.locator('.wizard-step a, .nav-link, .step-title').filter(
            has_text=re.compile(re.escape(texto_contiene), re.IGNORECASE)
        ).first
        if locator.count():
            locator.click()
            page.wait_for_timeout(800)
            return True
    except Exception:
        pass
    try:
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
    except Exception:
        return False


def _cerrar_modales(page):
    """Cierra cualquier modal/overlay que esté abierto.

    IMPORTANTE: Solo busca botones DENTRO de contenedores modales (SweetAlert,
    Bootstrap modal, etc.) para evitar clickear botones del formulario principal
    como "Validar y Continuar" o "Aceptar".
    """
    try:
        page.wait_for_timeout(300)
        return page.evaluate("""() => {
        let count = 0;

        // ── SweetAlert ────────────────────────────────────────────────────
        const swalOverlay = document.querySelector('.swal-overlay--show-modal, .swal-overlay');
        if (swalOverlay && swalOverlay.offsetParent !== null) {
            // Intentar botón de confirmación primero, luego cualquier botón
            const okBtn = swalOverlay.querySelector(
                '.swal-button--confirm, .swal-button:not(.swal-button--cancel)'
            ) || swalOverlay.querySelector('.swal-button, button');
            if (okBtn) { okBtn.click(); count++; }
        }
        document.querySelectorAll('.swal-overlay, .swal-modal').forEach(el => {
            el.style.display = 'none'; count++;
        });

        // ── Bootstrap modales ─────────────────────────────────────────────
        // Solo buscar botones DENTRO de los contenedores de modal
        const modalContainers = document.querySelectorAll(
            '.modal.show, .modal.fade.show, [role="dialog"], .alert-dismissible'
        );
        for (const container of modalContainers) {
            for (const btn of container.querySelectorAll('button, a')) {
                const txt = btn.textContent.trim().toLowerCase();
                // Coincidencia EXACTA para evitar clickear "Validar y Continuar"
                if (['entendido', 'cerrar', 'close', 'aceptar', 'ok', 'si, enviar',
                     'sí, enviar', 'confirmar', 'dismiss'].includes(txt)) {
                    if (btn.offsetParent !== null) { btn.click(); count++; break; }
                }
            }
            container.classList.remove('show');
            container.style.display = 'none';
            count++;
        }
        document.querySelectorAll('.modal-backdrop').forEach(b => { b.remove(); count++; });
        document.body.classList.remove('modal-open');
        document.body.style.paddingRight = '';
        return count;
    }""")
    except Exception:
        return 0


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
    try:
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
    except Exception:
        return False


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


def _limpiar_telefono(telefono):
    """Retorna sólo los últimos 10 dígitos (sin código de país)."""
    import re as _re
    digits = _re.sub(r'\D', '', telefono or '')
    return digits[-10:] if len(digits) >= 10 else digits or '6641234567'


def _llenar_domicilio(page, vialidad, num_ext, cp, prefix='domicilio'):
    """Llena los campos de domicilio y espera al AJAX del CP para seleccionar municipio y colonia."""
    _select_option(page, f'{prefix}[estado_id]', '02')         # Baja California
    _select_option(page, f'{prefix}[tipo_vialidad_id]', '5')   # CALLE
    _fill_input(page, f'{prefix}[vialidad]', vialidad or 'Av Principal')
    _fill_input(page, f'{prefix}[num_ext]', num_ext or '123')

    # Llenar CP y disparar eventos para que el portal cargue colonia/municipio vía AJAX
    cp_val = cp or '22000'
    try:
        page.evaluate("""(args) => {
            const [name, val] = args;
            const el = document.querySelector(`[name="${name}"]`);
            if (el) {
                el.focus();
                el.value = val;
                ['input', 'change', 'blur'].forEach(ev =>
                    el.dispatchEvent(new Event(ev, {bubbles: true})));
            }
        }""", [f'{prefix}[cp]', cp_val])
    except Exception:
        _fill_input(page, f'{prefix}[cp]', cp_val)

    # Esperar a que el AJAX cargue las opciones de colonia y municipio
    page.wait_for_timeout(3000)

    # Seleccionar primer municipio disponible (el portal lo carga según CP)
    try:
        page.evaluate("""(name) => {
            const sel = document.querySelector(`[name="${name}"]`);
            if (sel && sel.options.length > 1 && !sel.value) {
                sel.selectedIndex = 1;
                sel.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }""", 'municipio')
    except Exception:
        pass
    page.wait_for_timeout(500)

    # Seleccionar primer colonia/asentamiento disponible
    try:
        page.evaluate("""(name) => {
            const sel = document.querySelector(`[name="${name}"]`);
            if (sel && sel.options.length > 1) {
                sel.selectedIndex = 1;
                sel.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }""", f'{prefix}[asentamiento]')
    except Exception:
        pass
    page.wait_for_timeout(300)


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
    _fill_input(page, 'contactos[1]', _limpiar_telefono(cliente.telefono))

    # Domicilio con espera de AJAX para colonia/municipio
    _llenar_domicilio(page,
                      vialidad=cliente.direccion_calle,
                      num_ext=cliente.direccion_numero,
                      cp=cliente.direccion_cp)

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

    page.wait_for_timeout(500)

    # Click "Guardar" para cerrar el panel del solicitante
    _btn_click(page, 'guardar', timeout=5000)


def _llenar_citado(page, cliente):
    """Llena los campos del citado (empresa/patrón)."""
    empresa_nombre = cliente.empresa_razon_social or cliente.empresa or 'Empresa SA de CV'
    nombre_parts = empresa_nombre.split()

    # Tipo persona: desde el modelo (Física o Moral)
    tipo_persona_id = TIPO_PERSONA_PORTAL_IDS.get(cliente.tipo_persona_citado, '1')
    _click_radio(page, 'solicitado[tipo_persona_id]', tipo_persona_id)
    page.wait_for_timeout(300)

    # Datos del citado
    _fill_input(page, 'solicitado[nombre]', nombre_parts[0] if nombre_parts else 'Empresa')
    _fill_input(page, 'solicitado[primer_apellido]', nombre_parts[1] if len(nombre_parts) > 1 else 'SA')
    _fill_input(page, 'solicitado[segundo_apellido]',
                'de CV' if len(nombre_parts) <= 2 else ' '.join(nombre_parts[2:]))
    _select_option(page, 'solicitado[genero_id]', '1')             # MASCULINO
    _select_option(page, 'solicitado[nacionalidad_id]', '1')       # MEXICANA

    # Domicilio del citado con espera de AJAX para colonia/municipio
    _llenar_domicilio(page,
                      vialidad=cliente.empresa_calle or cliente.direccion_calle,
                      num_ext=cliente.empresa_numero or cliente.direccion_numero,
                      cp=cliente.empresa_cp or cliente.direccion_cp)

    # Teléfono de contacto
    _fill_input(page, 'contactos[1]', _limpiar_telefono(cliente.empresa_telefono or cliente.telefono))

    page.wait_for_timeout(500)

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
            force_headless = os.environ.get('FORCE_HEADLESS', 'true').lower() == 'true'
            actual_headless = headless if not force_headless else True

            browser = p.chromium.launch(
                headless=actual_headless,
                slow_mo=300 if not actual_headless else 50,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
                timeout=15000,
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
                page.goto(URL_SOLICITUD, wait_until='networkidle', timeout=20000)
            except PwTimeout:
                page.goto(URL_SOLICITUD, timeout=20000)
            page.wait_for_timeout(1000)
            checkpoint('00_inicio')

            # ════════════════════════════════════════════════════════════════
            #  FASE 1: Aviso de Privacidad
            # ════════════════════════════════════════════════════════════════
            logger.info('[1] Aceptando aviso de privacidad...')

            # Seleccionar radio "Acepto" (radioAviso = '1')
            _click_radio(page, 'radioAviso', '1')
            page.wait_for_timeout(200)

            # Click "Aceptar"
            _btn_click(page, 'Aceptar')
            page.wait_for_timeout(500)

            # Cerrar modales que aparezcan
            _cerrar_modales(page)
            page.wait_for_timeout(500)
            checkpoint('01_aviso_aceptado')

            # ════════════════════════════════════════════════════════════════
            #  FASE 2: Industria
            # ════════════════════════════════════════════════════════════════
            logger.info('[2] Seleccionando industria...')

            # Seleccionar "Ninguna de las anteriores" (industria = 28)
            _click_radio(page, 'industria', '28')
            page.wait_for_timeout(500)

            # Cerrar modal informativo que pueda aparecer
            _cerrar_modales(page)
            page.wait_for_timeout(200)

            # Click "Validar y Continuar"
            _click_validar_continuar(page)
            page.wait_for_timeout(1000)

            # Cerrar modales
            _cerrar_modales(page)
            page.wait_for_timeout(500)
            checkpoint('02_industria')

            # ════════════════════════════════════════════════════════════════
            #  FASE 3: Fecha de conflicto y objeto de la solicitud
            # ════════════════════════════════════════════════════════════════
            logger.info('[3] Llenando fecha y objeto...')

            # Llenar fecha de conflicto y cerrar el date-picker que se abre
            _fill_input(page, 'solicitud[fecha_conflicto]', fmt_fecha(fecha_conflicto))
            # Escape cierra el calendario sin borrar el valor ya seteado
            try:
                page.keyboard.press('Escape')
            except Exception:
                pass
            page.wait_for_timeout(400)

            # Diagnóstico: listar todos los selects en la página para confirmar nombres
            try:
                selects_info = page.evaluate("""() =>
                    Array.from(document.querySelectorAll('select')).map(s => ({
                        name: s.name, id: s.id,
                        opts: s.options.length,
                        val: s.value
                    }))
                """)
                logger.info('[3] Selects en página: %s', selects_info)
            except Exception:
                pass

            # Seleccionar objeto — usar selectedIndex=1 porque el valor numérico
            # varía por portal y setting el.value a un ID incorrecto falla silenciosamente
            try:
                objeto_texto = page.evaluate("""() => {
                    // Intentar el nombre conocido primero, luego buscar por heurística
                    let sel = document.querySelector('[name="solicitud[objeto_id]"]');
                    if (!sel) {
                        // Buscar el segundo select de la página (el primero podría ser otro)
                        const allSels = document.querySelectorAll('select');
                        for (const s of allSels) {
                            if (s.name && s.name.toLowerCase().includes('objeto')) {
                                sel = s; break;
                            }
                        }
                    }
                    if (sel && sel.options.length > 1) {
                        sel.selectedIndex = 1;
                        sel.dispatchEvent(new Event('change', {bubbles: true}));
                        return sel.options[1].text + ' [name=' + sel.name + ']';
                    }
                    return null;
                }""")
                logger.info('[3] Objeto seleccionado: %s', objeto_texto)
            except Exception as e:
                logger.warning('[3] Error al seleccionar objeto: %s', e)
            page.wait_for_timeout(300)

            # Click "Validar y Continuar"
            _click_validar_continuar(page)
            page.wait_for_timeout(1000)
            checkpoint('03_fecha_objeto')

            # ════════════════════════════════════════════════════════════════
            #  FASE 4: Solicitante (Trabajador)
            # ════════════════════════════════════════════════════════════════
            logger.info('[4] Llenando datos del solicitante...')

            # Navegar al tab "Solicitante"
            _navigate_wizard_tab(page, 'solicitante')
            page.wait_for_timeout(800)

            # Click "Agregar solicitante"
            _btn_click(page, 'agregar solicitante')
            page.wait_for_timeout(1500)

            # Llenar campos del solicitante
            _llenar_solicitante(page, cliente,
                                fmt_fecha(fecha_nac),
                                fmt_fecha(fecha_ing),
                                fmt_fecha(fecha_sal))
            page.wait_for_timeout(1000)
            checkpoint('04_solicitante')

            # Click "Validar y Continuar"
            _click_validar_continuar(page)
            page.wait_for_timeout(1000)
            checkpoint('04_solicitante_validado')

            # ════════════════════════════════════════════════════════════════
            #  FASE 5: Citado (Empresa/Patrón)
            # ════════════════════════════════════════════════════════════════
            logger.info('[5] Llenando datos del citado...')

            # Navegar al tab "Citado"
            _navigate_wizard_tab(page, 'citado')
            page.wait_for_timeout(800)

            # Click "Agregar citado"
            _btn_click(page, 'agregar citado')
            page.wait_for_timeout(1500)

            # Llenar campos del citado
            _llenar_citado(page, cliente)
            page.wait_for_timeout(1000)
            checkpoint('05_citado')

            # Click "Validar y Continuar"
            _click_validar_continuar(page)
            page.wait_for_timeout(1500)
            # Wait for any portal-side navigation triggered by Validar y Continuar
            try:
                page.wait_for_load_state('domcontentloaded', timeout=5000)
            except Exception:
                pass
            checkpoint('05_citado_validado')

            # ════════════════════════════════════════════════════════════════
            #  FASE 6: Descripción de los hechos
            # ════════════════════════════════════════════════════════════════
            logger.info('[6] Llenando descripción de los hechos...')

            # Navegar al tab "Descripción"
            _navigate_wizard_tab(page, 'descripci')
            page.wait_for_timeout(800)

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

            # Llenar textarea con JS (evita interceptación de SweetAlert/modales)
            try:
                page.evaluate("""(texto) => {
                    const ta = document.querySelector('textarea');
                    if (ta) {
                        ta.focus();
                        ta.value = texto;
                        ta.dispatchEvent(new Event('input', {bubbles: true}));
                        ta.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }""", texto_hechos)
            except Exception:
                pass
            page.wait_for_timeout(300)

            # Click "Aceptar"
            _btn_click(page, 'aceptar')
            page.wait_for_timeout(1000)
            checkpoint('06_descripcion')

            # ════════════════════════════════════════════════════════════════
            #  FASE 7: Resumen y Envío
            # ════════════════════════════════════════════════════════════════
            logger.info('[7] Navegando a resumen y enviando...')

            # Navegar al tab "Resumen"
            _navigate_wizard_tab(page, 'resumen')
            page.wait_for_timeout(1000)

            # Verificar errores antes de enviar
            try:
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
            except Exception:
                errores = []
            if errores:
                logger.warning('  Errores detectados antes de enviar: %s', errores)
                for err in errores[:3]:
                    logger.warning('  Error: %s (campo: %s)', err['msg'], err['name'])

            # ════════════════════════════════════════════════════════════
            #  FASE 7: Envío de la solicitud con manejo de navegación
            # ════════════════════════════════════════════════════════════
            #
            # PROBLEMA: El portal navega a una nueva página al enviar
            # el formulario (ya sea al hacer clic en "Enviar solicitud"
            # o al confirmar con "Enviar"). La navegación DESTRUYE el
            # contexto de JS anterior, causando el error:
            #   "Execution context was destroyed"
            #
            # SOLUCIÓN: Usar expect_navigation() para:
            #  1. Crear un watcher de navegación ANTES de cualquier clic
            #  2. Hacer los clicks que disparan la navegación
            #  3. Esperar a que la navegación termine completamente
            #
            # El watcher cubre AMBOS clicks porque no sabemos cuál
            # de ellos dispara la navegación (puede variar según el
            # comportamiento actual del portal).
            # ════════════════════════════════════════════════════════════
            # ════════════════════════════════════════════════════════════
            #  FASE 7: Envío con expect_navigation + SweetAlert selector
            # ════════════════════════════════════════════════════════════
            #
            # ESTRATEGIA:
            #  1. expect_navigation() se activa ANTES de cualquier clic
            #  2. Se espera el SweetAlert específicamente (no timeout ciego)
            #  3. Se usa SOLO Playwright nativo para el clic (no evaluate)
            #  4. Si no hay SweetAlert, se asume que ya navegó
            #  5. Se detecta navegación comparando URLs
            # ════════════════════════════════════════════════════════════
            logger.info('[7] Iniciando envío con expect_navigation...')
            navegacion_completa = False
            url_inicial = page.url

            # 7a: Click "Enviar solicitud" - FUERA del expect_navigation
            # porque puede o no disparar navegación (SweetAlert puede aparecer antes)
            logger.info('[7a] Click en Enviar solicitud...')
            _btn_click(page, 'enviar solicitud')

            # Esperar SweetAlert por máximo 1.5s (si no aparece, el envío es directo)
            try:
                page.wait_for_selector('.swal-overlay, .swal-modal, .modal.show', timeout=1500)
                logger.info('[7a] SweetAlert detectado')
                page.wait_for_timeout(300)
            except Exception:
                logger.info('[7a] Sin SweetAlert - navegación directa')

            try:
                with page.expect_navigation(timeout=45000):
                    # 7b: Click botón de confirmación del SweetAlert (si apareció)
                    # Usar selector específico de SweetAlert para evitar clickear
                    # "Enviar solicitud" del fondo de la página por error
                    logger.info('[7b] Click en confirmar SweetAlert...')
                    confirmed = False
                    for sel in [
                        '.swal-button--confirm',
                        '.swal-button:not(.swal-button--cancel)',
                        'button.swal-button',
                    ]:
                        try:
                            btn = page.locator(sel).first
                            if btn.count() > 0:
                                btn.click(timeout=3000)
                                logger.info('[7b] Confirmado con selector: %s', sel)
                                confirmed = True
                                break
                        except Exception:
                            continue
                    if not confirmed:
                        logger.info('[7b] Sin SweetAlert visible - navegación directa')

                navegacion_completa = True
                logger.info('[7] Navegación detectada! URL: %s → %s', url_inicial, page.url)
            except Exception as nav_err:
                logger.warning('[7] expect_navigation falló: %s', nav_err)
                # Detectar si navegó a pesar del error
                try:
                    url_actual = page.url
                    if url_actual and url_actual != url_inicial:
                        logger.info('[7] Navegación detectada por cambio de URL: %s', url_actual)
                        navegacion_completa = True
                    else:
                        logger.info('[7] URL sin cambios: %s', url_actual)
                except Exception:
                    logger.warning('[7] No se pudo obtener URL')

            if not navegacion_completa:
                logger.info('[7] Fallback: esperando carga de página...')
                try:
                    page.wait_for_load_state('networkidle', timeout=10000)
                    logger.info('[7] load_state completado (fallback)')
                except Exception:
                    page.wait_for_timeout(3000)
                try:
                    if page.url != url_inicial:
                        navegacion_completa = True
                        logger.info('[7] Navegación confirmada en fallback: %s', page.url)
                except Exception:
                    pass

            # Asegurar que el DOM de la nueva página esté listo
            try:
                page.wait_for_load_state('domcontentloaded', timeout=10000)
            except Exception:
                pass

            page.wait_for_timeout(1000)

            # Cerrar modal de éxito (ahora en la NUEVA página si navegó)
            _cerrar_modales(page)
            page.wait_for_timeout(500)
            checkpoint('07_enviado')

            # ════════════════════════════════════════════════════════════════
            #  FASE 8: Extraer folio + Descargar acuse PDF
            # ════════════════════════════════════════════════════════════════
            logger.info('[8] Extrayendo folio y descargando acuse...')

            # ── 8a: Extraer folio del texto de la página de confirmación ──
            # La página en /solicitud/update muestra el folio prominentemente.
            # Intentamos antes de cualquier click para no perder el contexto.
            texto_pagina = ''
            try:
                texto_pagina = page.inner_text('body')
                logger.info('[8] Texto de página de confirmación: %s...', texto_pagina[:600].replace('\n', ' | '))

                FOLIO_PATTERNS = [
                    # Etiqueta explícita seguida de folio
                    r'[Ff]olio[:\s#Nº°\.]*([A-Z0-9][-A-Z0-9/]+)',
                    r'N[úu]mero\s+de\s+[Ss]olicitud[:\s]*([A-Z0-9][-A-Z0-9/]+)',
                    r'N[úu]mero\s+de\s+[Ff]olio[:\s]*([A-Z0-9][-A-Z0-9/]+)',
                    r'[Ss]olicitud\s+N[°º]?[:\s]*([A-Z0-9][-A-Z0-9/]+)',
                    r'Expediente[:\s#]*([A-Z0-9][-A-Z0-9/]+)',
                    # Formatos típicos del portal BC
                    r'(CCL[-/][A-Z0-9/-]+)',
                    r'(BCN?[-/][A-Z0-9/-]+)',
                    r'(CFFL[-/][A-Z0-9/-]+)',
                    r'(BC[-/]CCFL[-/][A-Z0-9/-]+)',
                    # Número de 4 dígitos (año) guion número
                    r'\b(\d{4}[-/]\d{4,8})\b',
                ]
                for pat in FOLIO_PATTERNS:
                    m = re.search(pat, texto_pagina)
                    if m:
                        folio_candidato = (m.group(1) if m.lastindex else m.group(0)).strip().rstrip('.')
                        logger.info('[8] Folio encontrado en página con patrón "%s": %s', pat, folio_candidato)
                        resultado.folio = folio_candidato
                        resultado.success = True
                        break

                if not resultado.folio:
                    logger.warning('[8] No se encontró folio en el texto de la página')
                    logger.info('[8] Texto completo para diagnóstico: %s', texto_pagina[:1500])
            except Exception as e:
                logger.warning('[8] Error al extraer texto de página: %s', e)

            # ── 8b: Intentar descargar el PDF del acuse ───────────────────
            # Probamos múltiples textos de botón que el portal podría usar
            for texto_btn in ['acuse', 'descargar', 'pdf', 'comprobante', 'recibo',
                              'imprimir', 'constancia', 'documento']:
                _btn_click(page, texto_btn)
                page.wait_for_timeout(600)

            # Esperar a que la descarga termine
            try:
                page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(2000)

            checkpoint('08_confirmacion')

            # ── 8c: Si se descargó un PDF, extraer folio de él también ───
            if pdf_descargado:
                pdf_path = Path(pdf_descargado)
                resultado.pdf_path = str(pdf_path)
                nombre_pdf = pdf_path.stem
                logger.info('[8] PDF descargado: %s', nombre_pdf)

                # Folio desde el nombre del archivo
                if not resultado.folio:
                    for pat in [r'(CCL[-/][\w/-]+)', r'(\d{4}[-/]\d{4,8})', r'([\w-]+folio[\w-]*)']:
                        m = re.search(pat, nombre_pdf, re.IGNORECASE)
                        if m:
                            resultado.folio = m.group(1)
                            break

                # Folio desde el contenido del PDF
                if not resultado.folio:
                    try:
                        with open(pdf_descargado, 'rb') as f:
                            contenido = f.read()
                        texto_pdf = contenido.decode('latin-1', errors='ignore')
                        for pat in [r'(CCL[:\s]*/[\d\-]+)', r'FOLIO[:\s]*([\w/-]+)',
                                    r'N[úu]mero[:\s]*([\w/-]+)', r'(\d{4}[-/]\d{4,8})']:
                            m = re.search(pat, texto_pdf, re.IGNORECASE)
                            if m:
                                resultado.folio = m.group(1).strip()
                                break
                    except Exception as e:
                        logger.warning('[8] No se pudo leer PDF: %s', e)

                resultado.success = True
                resultado.detalle = f'Solicitud enviada. Folio: {resultado.folio or "N/A"}'
                logger.info('[8] Éxito con PDF. Folio=%s', resultado.folio)

            elif resultado.success and resultado.folio:
                # Folio encontrado en texto aunque sin PDF
                resultado.detalle = f'Solicitud enviada. Folio: {resultado.folio} (sin PDF)'
                logger.info('[8] Éxito sin PDF. Folio=%s', resultado.folio)

            else:
                # ── 8d: Buscar enlace de descarga como último recurso ─────
                try:
                    doc_url = page.evaluate("""() => {
                        const sel = 'a[href*="getFile"], a[href*="acuse"], a[href*="documento"], a[href*="folio"], a[href*=".pdf"]';
                        for (const link of document.querySelectorAll(sel)) {
                            if (link.href) return link.href;
                        }
                        return '';
                    }""")
                except Exception:
                    doc_url = ''

                if doc_url:
                    resultado.detalle = f'Solicitud enviada. URL documento: {doc_url}'
                    m = re.search(r'getFile/([\w-]+)|folio=([\w-]+)', doc_url)
                    if m:
                        resultado.folio = (m.group(1) or m.group(2))
                        resultado.success = True
                else:
                    resultado.error = 'Solicitud enviada al portal pero no se pudo obtener el folio'
                    try:
                        url_final = page.url
                    except Exception:
                        url_final = 'desconocida'
                    # Store page text so it's visible in the task detalle for debugging
                    resultado.detalle = f'URL={url_final} | TEXTO={texto_pagina[:800]}'

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
