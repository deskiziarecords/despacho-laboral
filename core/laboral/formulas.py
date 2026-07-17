"""
Fórmulas Matemáticas Puras para Cálculos Laborales Mexicanos
=============================================================

Este módulo NO tiene dependencias de Django.
Contiene SOLO lógica matemática: recibe números, devuelve números.
Las reglas legales (días de vacaciones, topes, UMAs) se las pasa quien llama.

Autor: Conciliacion Laboral Tijuana - Motor Jurídico Parametrizable
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Optional


# ─── Utilidades ────────────────────────────────────────────────────────────

def _decimal(valor, digitos=2) -> Decimal:
    """Convierte a Decimal con redondeo bancario."""
    return Decimal(str(valor)).quantize(Decimal(f'0.{"0" * digitos}'), rounding=ROUND_HALF_UP)


def dias_entre(fecha_inicio: date, fecha_fin: date) -> int:
    """Días calendario entre dos fechas (incluyendo fracciones)."""
    return (fecha_fin - fecha_inicio).days


def años_completos(fecha_inicio: date, fecha_fin: date) -> Decimal:
    """Años completos (incluye fracción)."""
    dias = dias_entre(fecha_inicio, fecha_fin)
    if dias < 0:
        return Decimal('0')
    return _decimal(dias / Decimal('365'), 4)


# ─── Salario ───────────────────────────────────────────────────────────────

def salario_diario(salario: Decimal, periodo: str = 'mensual') -> Decimal:
    """
    Calcula el salario diario según el periodo de pago.

    Args:
        salario: Monto del salario en el periodo
        periodo: 'mensual' (÷30), 'quincenal' (÷15), 'semanal' (÷7), 'diario' (×1)

    Returns:
        Salario diario calculado
    """
    divisores = {
        'mensual': Decimal('30'),
        'quincenal': Decimal('15'),
        'semanal': Decimal('7'),
        'diario': Decimal('1'),
    }
    divisor = divisores.get(periodo, Decimal('30'))
    return _decimal(salario / divisor)


# ─── 1. Aguinaldo Proporcional ─────────────────────────────────────────────

def aguinaldo_proporcional(
    dias_trabajados: int,
    salario_diario_valor: Decimal,
    dias_aguinaldo: int = 15
) -> Decimal:
    """
    Aguinaldo proporcional = (días_trabajados / 365) × días_aguinaldo × salario_diario

    Args:
        dias_trabajados: Días laborados en el año
        salario_diario_valor: Salario diario del trabajador
        dias_aguinaldo: Días de aguinaldo que otorga la ley (mínimo 15)

    Returns:
        Aguinaldo proporcional calculado
    """
    if dias_trabajados <= 0 or salario_diario_valor <= 0:
        return Decimal('0')
    return _decimal(
        (Decimal(str(dias_trabajados)) / Decimal('365'))
        * Decimal(str(dias_aguinaldo))
        * salario_diario_valor
    )


# ─── 2. Vacaciones Proporcionales ──────────────────────────────────────────

def vacaciones_proporcionales(
    dias_trabajados: int,
    dias_vacaciones: int,
    salario_diario_valor: Decimal
) -> Decimal:
    """
    Vacaciones proporcionales = (días_trabajados / 365) × días_vacaciones × salario_diario

    Args:
        dias_trabajados: Días laborados
        dias_vacaciones: Días de vacaciones que corresponden según antigüedad
        salario_diario_valor: Salario diario del trabajador

    Returns:
        Vacaciones proporcionales calculadas
    """
    if dias_trabajados <= 0 or dias_vacaciones <= 0 or salario_diario_valor <= 0:
        return Decimal('0')
    return _decimal(
        (Decimal(str(dias_trabajados)) / Decimal('365'))
        * Decimal(str(dias_vacaciones))
        * salario_diario_valor
    )


# ─── 3. Prima Vacacional ───────────────────────────────────────────────────

def prima_vacacional(
    vacaciones_proporcionales_valor: Decimal,
    porcentaje_prima: Decimal = Decimal('0.25')
) -> Decimal:
    """
    Prima vacacional = vacaciones_proporcionales × porcentaje_prima

    Args:
        vacaciones_proporcionales_valor: Monto de vacaciones proporcionales
        porcentaje_prima: Porcentaje de prima vacacional (mínimo 25% = 0.25)

    Returns:
        Prima vacacional calculada
    """
    if vacaciones_proporcionales_valor <= 0:
        return Decimal('0')
    return _decimal(vacaciones_proporcionales_valor * porcentaje_prima)


# ─── 4. Prima de Antigüedad ────────────────────────────────────────────────

def prima_antiguedad(
    años_trabajados: Decimal,
    salario_diario_valor: Decimal,
    dias_por_año: int = 12,
    salario_tope: Optional[Decimal] = None
) -> Decimal:
    """
    Prima de antigüedad = 12 × años_trabajados × salario_diario (con tope)

    La prima de antigüedad se calcula con 12 días de salario por cada año trabajado.
    El salario diario está TOPEADO a 2 UMAs o 2 salarios mínimos (según aplique).

    Args:
        años_trabajados: Años laborados (con fracción)
        salario_diario_valor: Salario diario (se aplicará tope si se proporciona)
        dias_por_año: Días por año (normalmente 12)
        salario_tope: Tope salarial diario (ej: 2 × UMA diaria)

    Returns:
        Prima de antigüedad calculada
    """
    if años_trabajados <= 0 or salario_diario_valor <= 0:
        return Decimal('0')

    # Aplicar tope si existe
    salario_base = salario_diario_valor
    if salario_tope is not None and salario_diario_valor > salario_tope:
        salario_base = salario_tope

    return _decimal(
        Decimal(str(dias_por_año))
        * años_trabajados
        * salario_base
    )


# ─── 5. Indemnización Constitucional (3 meses) ─────────────────────────────

def indemnizacion_constitucional(salario_diario_valor: Decimal) -> Decimal:
    """
    Indemnización constitucional = 90 × salario_diario

    Conforme al artículo 50 LFT (3 meses de salario).

    Args:
        salario_diario_valor: Salario diario del trabajador

    Returns:
        Indemnización de 3 meses
    """
    if salario_diario_valor <= 0:
        return Decimal('0')
    return _decimal(Decimal('90') * salario_diario_valor)


# ─── 6. Indemnización 20 días por año ──────────────────────────────────────

def indemnizacion_20dias_por_ano(
    años_trabajados: Decimal,
    salario_diario_valor: Decimal,
    salario_tope: Optional[Decimal] = None
) -> Decimal:
    """
    Indemnización 20 días de salario por cada año de servicios.

    Conforme al artículo 50 fracción II LFT: 20 días de salario
    por cada año de servicios prestados, con tope de 2 × UMA/SM.

    Args:
        años_trabajados: Años trabajados (incluye fracción)
        salario_diario_valor: Salario diario (se aplica tope)
        salario_tope: Tope salarial diario

    Returns:
        Indemnización 20 días por año
    """
    if años_trabajados <= 0 or salario_diario_valor <= 0:
        return Decimal('0')
    salario_base = salario_diario_valor
    if salario_tope is not None and salario_diario_valor > salario_tope:
        salario_base = salario_tope
    return _decimal(Decimal('20') * años_trabajados * salario_base)


# ─── 7. Vacaciones Vencidas ───────────────────────────────────────────────

def vacaciones_vencidas(
    dias_vencidos: int,
    salario_diario_valor: Decimal
) -> Decimal:
    """
    Vacaciones vencidas de años anteriores no pagadas.

    Args:
        dias_vencidos: Días de vacaciones no pagadas de años anteriores
        salario_diario_valor: Salario diario del trabajador

    Returns:
        Monto de vacaciones vencidas
    """
    if dias_vencidos <= 0 or salario_diario_valor <= 0:
        return Decimal('0')
    return _decimal(Decimal(str(dias_vencidos)) * salario_diario_valor)


# ─── 8. Horas Extras ──────────────────────────────────────────────────────

def horas_extras(
    cantidad_horas: Decimal,
    salario_diario_valor: Decimal
) -> Decimal:
    """
    Cálculo de horas extra (doble + triple).
    
    Se calcula el valor hora ordinario y se aplica:
    - Horas extra dobles (primeras 9 hrs/semana): 2× valor hora
    - Horas extra triples (excedentes): 3× valor hora
    
    Para simplificar, se usa un factor promedio de 2.5× por hora.

    Args:
        cantidad_horas: Número total de horas extra
        salario_diario_valor: Salario diario del trabajador

    Returns:
        Monto de horas extra
    """
    if cantidad_horas <= 0 or salario_diario_valor <= 0:
        return Decimal('0')
    # Valor hora ordinario = salario diario / 8 horas
    valor_hora = salario_diario_valor / Decimal('8')
    # Factor promedio ponderado: dobles (2) y triples (3) → ~2.5
    return _decimal(cantidad_horas * valor_hora * Decimal('2.5'))


# ─── 9. Días Festivos ─────────────────────────────────────────────────────

def dias_festivos(
    cantidad_dias: int,
    salario_diario_valor: Decimal
) -> Decimal:
    """
    Días festivos laborados no pagados.
    
    Conforme al Art. 75 LFT: si se trabaja en día festivo,
    se paga triple (salario ordinario + 200% extra).
    Monto = días × salario_diario × 3

    Args:
        cantidad_dias: Número de días festivos trabajados
        salario_diario_valor: Salario diario del trabajador

    Returns:
        Monto de días festivos
    """
    if cantidad_dias <= 0 or salario_diario_valor <= 0:
        return Decimal('0')
    return _decimal(Decimal(str(cantidad_dias)) * salario_diario_valor * Decimal('3'))


# ─── 10. Total General ────────────────────────────────────────────────────────

def total_prestaciones(
    *montos: Decimal
) -> Decimal:
    """Suma todas las prestaciones calculadas."""
    suma = sum(montos, Decimal('0'))
    return _decimal(suma)
