"""
Calculadoras / Orquestadores para Cálculos Laborales
=====================================================

Combina:
  - Datos del expediente (fechas, salario, periodo de pago)
  - Reglas legales (tabla vacaciones, UMA, topes)
  - Fórmulas puras (formulas.py)

Devuelve diccionarios listos para mostrar en la UI o guardar en CalculoLaboral.

Autor: Conciliacion Laboral Tijuana - Motor Jurídico Parametrizable
"""

from decimal import Decimal
from datetime import date
from typing import Optional, Dict, Any

from . import formulas as f
from . import rules as r


def calcular_todo(
    fecha_ingreso: date,
    fecha_salida: date,
    salario: Decimal,
    periodo_pago: str = 'mensual',
    umas: Optional[Dict[str, Decimal]] = None,
) -> Dict[str, Any]:
    """
    Calcula TODAS las prestaciones laborales de una sola vez.

    Args:
        fecha_ingreso: Fecha de inicio de la relación laboral
        fecha_salida: Fecha de término / despido
        salario: Salario base (en el periodo indicado)
        periodo_pago: 'mensual', 'quincenal', 'semanal', 'diario'
        umas: Diccionario opcional con valores de UMA, salario_minimo, etc.

    Returns:
        Dict con todos los cálculos +
        {
            'salario_diario': Decimal,
            'dias_trabajados': int,
            'años_trabajados': Decimal,
            'aguinaldo': Decimal,
            'vacaciones': {'dias': int, 'monto': Decimal},
            'prima_vacacional': Decimal,
            'prima_antiguedad': Decimal,
            'indemnizacion': Decimal,
            'total': Decimal,
            'detalles': {...}
        }
    """
    # ─── Preparar datos base ───────────────────────────────────────────
    sd = f.salario_diario(salario, periodo_pago)
    dias = f.dias_entre(fecha_ingreso, fecha_salida)
    años = f.años_completos(fecha_ingreso, fecha_salida)

    if dias <= 0 or sd <= 0:
        return _resultado_vacio("Fechas inválidas o salario no especificado")

    # ─── 1. Aguinaldo Proporcional ─────────────────────────────────────
    aguinaldo_dias = r.ReglasPorDefecto.AGUINALDO_DIAS
    aguinaldo = f.aguinaldo_proporcional(dias, sd, aguinaldo_dias)

    # ─── 2. Vacaciones Proporcionales ──────────────────────────────────
    años_enteros = int(años)
    dias_vacaciones = r.obtener_dias_vacaciones(años_enteros)

    # Si no cumple el año, calcular proporcional
    if años_enteros < 1:
        # Proporcional al tiempo trabajado
        meses_trabajados = dias / 365 * 12
        # Si tiene menos de 1 año, no le corresponden vacaciones completas
        # pero se puede calcular proporcional:
        dias_vacaciones_proporcional = max(0, int(dias / 365 * 12))
        vac_monto = f.vacaciones_proporcionales(dias, dias_vacaciones_proporcional, sd)
        dias_vacaciones_reales = dias_vacaciones
    else:
        vac_monto = f.vacaciones_proporcionales(dias, dias_vacaciones, sd)
        dias_vacaciones_reales = dias_vacaciones

    # ─── 3. Prima Vacacional ───────────────────────────────────────────
    prima_vac = f.prima_vacacional(
        vac_monto,
        r.ReglasPorDefecto.PRIMA_VACACIONAL_PORCENTAJE
    )

    # ─── 4. Prima de Antigüedad ────────────────────────────────────────
    tope = r.ReglasPorDefecto.obtener_tope_salarial()
    prima_ant = f.prima_antiguedad(
        años,
        sd,
        r.ReglasPorDefecto.PRIMA_ANTIGUEDAD_DIAS_POR_ANO,
        tope
    )

    # ─── 5. Indemnización Constitucional ───────────────────────────────
    indemnizacion = f.indemnizacion_constitucional(sd)

    # ─── 6. Total ──────────────────────────────────────────────────────
    total = f.total_prestaciones(aguinaldo, vac_monto, prima_vac, prima_ant, indemnizacion)

    return {
        'success': True,
        'salario_diario': sd,
        'dias_trabajados': dias,
        'años_trabajados': años,
        'años_enteros': años_enteros,
        'periodo_pago': periodo_pago,
        'aguinaldo': {
            'dias_ley': aguinaldo_dias,
            'monto': aguinaldo,
        },
        'vacaciones': {
            'dias_segun_antiguedad': dias_vacaciones_reales,
            'monto': vac_monto,
        },
        'prima_vacacional': {
            'porcentaje': float(r.ReglasPorDefecto.PRIMA_VACACIONAL_PORCENTAJE * 100),
            'monto': prima_vac,
        },
        'prima_antiguedad': {
            'dias_por_año': r.ReglasPorDefecto.PRIMA_ANTIGUEDAD_DIAS_POR_ANO,
            'tope_diario': tope,
            'tope_aplicado': sd > tope,
            'monto': prima_ant,
        },
        'indemnizacion': {
            'dias': r.ReglasPorDefecto.INDEMNIZACION_DIAS,
            'monto': indemnizacion,
        },
        'total': total,
        'detalles': {
            'fecha_ingreso': fecha_ingreso.isoformat(),
            'fecha_salida': fecha_salida.isoformat(),
            'salario_mensual': salario,
            'uma_diaria': r.ReglasPorDefecto.UMA_DIARIA,
        },
    }


def simular(
    salario: Decimal,
    fecha_ingreso: date,
    fecha_salida: date,
    periodo_pago: str = 'mensual',
) -> Dict[str, Any]:
    """
    Simulación rápida para el asesor.
    Recibe los mismos parámetros, devuelve resumen simplificado.
    """
    resultado = calcular_todo(fecha_ingreso, fecha_salida, salario, periodo_pago)
    if not resultado['success']:
        return resultado

    return {
        'success': True,
        'salario_diario': resultado['salario_diario'],
        'dias_trabajados': resultado['dias_trabajados'],
        'años_trabajados': resultado['años_trabajados'],
        'total': resultado['total'],
        'desglose': {
            'aguinaldo': resultado['aguinaldo']['monto'],
            'vacaciones': resultado['vacaciones']['monto'],
            'prima_vacacional': resultado['prima_vacacional']['monto'],
            'prima_antiguedad': resultado['prima_antiguedad']['monto'],
            'indemnizacion': resultado['indemnizacion']['monto'],
        },
    }


def _resultado_vacio(razon: str = "") -> Dict[str, Any]:
    """Retorna un dict de error."""
    return {
        'success': False,
        'error': razon,
        'salario_diario': Decimal('0'),
        'dias_trabajados': 0,
        'años_trabajados': Decimal('0'),
        'aguinaldo': {'dias_ley': 15, 'monto': Decimal('0')},
        'vacaciones': {'dias_segun_antiguedad': 0, 'monto': Decimal('0')},
        'prima_vacacional': {'porcentaje': 25, 'monto': Decimal('0')},
        'prima_antiguedad': {'dias_por_año': 12, 'tope_diario': Decimal('0'), 'tope_aplicado': False, 'monto': Decimal('0')},
        'indemnizacion': {'dias': 90, 'monto': Decimal('0')},
        'total': Decimal('0'),
        'detalles': {},
    }
