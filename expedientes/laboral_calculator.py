"""
Puente entre modelos Django y el Motor Jurídico de Cálculos Laborales
=====================================================================

Conecta los datos de CalculoLaboral / Cliente con core/laboral/calculators.py
y core/laboral/rules.py.

Autor: Despacho Laboral
"""

from decimal import Decimal
from datetime import date
from typing import Dict, Any

from django.utils import timezone

from core.laboral import calculators, rules


def calcular_desde_expediente(expediente) -> Dict[str, Any]:
    """
    Ejecuta el cálculo completo usando los datos del expediente y su cliente.

    Args:
        expediente: Instancia del modelo Expediente

    Returns:
        Dict con resultados de calcular_todo()
    """
    cliente = expediente.cliente

    # Obtener datos base
    fecha_ingreso = cliente.fecha_ingreso
    fecha_salida = cliente.fecha_salida
    salario = cliente.salario or Decimal('0')

    # Intentar obtener periodo de pago desde la solicitud de conciliación
    periodo_pago = 'mensual'
    try:
        if hasattr(expediente, 'solicitud') and expediente.solicitud.periodo_pago:
            # Mapear periodo de solicitud a periodo de cálculo
            mapa = {'diario': 'diario', 'semanal': 'semanal', 'quincenal': 'quincenal'}
            periodo_pago = mapa.get(expediente.solicitud.periodo_pago, 'mensual')
    except Exception:
        pass

    if not fecha_ingreso or not fecha_salida or salario <= 0:
        return calculators._resultado_vacio(
            "Completa los datos del cliente: fecha de ingreso, fecha de salida y salario"
        )

    return calculators.calcular_todo(
        fecha_ingreso=fecha_ingreso,
        fecha_salida=fecha_salida,
        salario=salario,
        periodo_pago=periodo_pago,
    )


def recalcular_calculo(calculo_laboral) -> None:
    """
    Recalcula y actualiza los campos de una instancia de CalculoLaboral.
    No guarda (el llamador debe hacer save()).

    Args:
        calculo_laboral: Instancia de CalculoLaboral
    """
    expediente = calculo_laboral.expediente
    resultado = calcular_desde_expediente(expediente)

    if not resultado['success']:
        return

    # Actualizar campos
    calculo_laboral.salario_mensual = expediente.cliente.salario or Decimal('0')
    calculo_laboral.salario_diario = resultado['salario_diario']
    calculo_laboral.fecha_ingreso = expediente.cliente.fecha_ingreso
    calculo_laboral.fecha_salida = expediente.cliente.fecha_salida
    calculo_laboral.dias_trabajados = resultado['dias_trabajados']
    calculo_laboral.años_trabajados = resultado['años_trabajados']
    calculo_laboral.aguinaldo = resultado['aguinaldo']['monto']
    calculo_laboral.vacaciones = resultado['vacaciones']['monto']
    calculo_laboral.dias_vacaciones = resultado['vacaciones']['dias_segun_antiguedad']
    calculo_laboral.prima_vacacional = resultado['prima_vacacional']['monto']
    calculo_laboral.prima_antiguedad = resultado['prima_antiguedad']['monto']
    calculo_laboral.tope_salarial_aplicado = resultado['prima_antiguedad']['tope_aplicado']
    calculo_laboral.indemnizacion = resultado['indemnizacion']['monto']
    calculo_laboral.total = resultado['total']
    calculo_laboral.recalculado_en = timezone.now()
