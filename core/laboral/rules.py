"""
Reglas Legales Configurables para Cálculos Laborales Mexicanos
==============================================================

Tablas legales con valores por defecto actualizados.
TODO se puede sobreescribir desde LegalConfig en la base de datos.

Autor: Despacho Laboral - Motor Jurídico Parametrizable
"""

from decimal import Decimal
from typing import Dict, List, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# TABLA DE VACACIONES (México - Reforma 2023)
# ═══════════════════════════════════════════════════════════════════════════
#
# Artículo 76 LFT: Primer año → 12 días, aumenta 2 cada año hasta 20.
# Después aumenta 2 cada 5 años.
#
# Ejemplo:
#   1 año  → 12 días
#   2 años → 14 días
#   3 años → 16 días
#   4 años → 18 días
#   5 años → 20 días
#  10 años → 22 días
#  15 años → 24 días
#  ...

TABLA_VACACIONES: List[Tuple[int, int]] = [
    (1, 12),    # 1 año → 12 días
    (2, 14),    # 2 años → 14 días
    (3, 16),    # 3 años → 16 días
    (4, 18),    # 4 años → 18 días
    (5, 20),    # 5 años → 20 días
    (10, 22),   # 10 años → 22 días
    (15, 24),   # 15 años → 24 días
    (20, 26),   # 20 años → 26 días
    (25, 28),   # 25 años → 28 días
    (30, 30),   # 30 años → 30 días
]


def obtener_dias_vacaciones(años_completos: int, tabla: List[Tuple[int, int]] = None) -> int:
    """
    Obtiene los días de vacaciones según la tabla de antigüedad.

    Args:
        años_completos: Años trabajados (número entero, se trunca)
        tabla: Lista de tuplas (años, días). Si es None, usa la tabla por defecto.

    Returns:
        Días de vacaciones que corresponden
    """
    if tabla is None:
        tabla = TABLA_VACACIONES

    if años_completos < 1:
        # Menos de 1 año: proporcional (todavía no cumple el año)
        return 0

    # Buscar en la tabla de mayor a menor
    for años, dias in reversed(tabla):
        if años_completos >= años:
            return dias

    # Si hay más años que el máximo de la tabla, extrapolar
    ultimos_años, ultimos_dias = tabla[-1]
    if años_completos > ultimos_años:
        # Cada 5 años adicionales → +2 días
        adicional = ((años_completos - ultimos_años) // 5) * 2
        return ultimos_dias + adicional

    return 12  # Default primer año


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTES LEGALES CONFIGURABLES
# ═══════════════════════════════════════════════════════════════════════════

class ReglasPorDefecto:
    """
    Valores legales por defecto (actualizados a la fecha).

    Estos valores se usan cuando NO hay un LegalConfig en la base de datos.
    Un administrador puede modificarlos desde el panel de admin.
    """

    # ─── UMA y Salario Mínimo ─────────────────────────────────────────
    # La UMA y el salario mínimo se actualizan anualmente.
    # Valores de referencia (2024):
    UMA_DIARIA = Decimal('108.57')        # UMA diaria 2024
    SALARIO_MINIMO = Decimal('248.93')     # Salario mínimo general 2024 (ZLF)
    SALARIO_MINIMO_FRONTERA = Decimal('374.89')  # Zona Libre Frontera Norte

    # ─── Topes ────────────────────────────────────────────────────────
    # La prima de antigüedad tiene un tope de 2 UMAs o 2 salarios mínimos
    TOPE_PRIMA_ANTIGUEDAD_TIPO = 'uma'     # 'uma' | 'salario_minimo' | 'frontera'
    TOPE_PRIMA_ANTIGUEDAD_MULTIPLO = 2     # 2 × UMA o 2 × salario mínimo

    # ─── Aguinaldo ────────────────────────────────────────────────────
    AGUINALDO_DIAS = 15                    # Mínimo legal: 15 días

    # ─── Prima Vacacional ─────────────────────────────────────────────
    PRIMA_VACACIONAL_PORCENTAJE = Decimal('0.25')  # Mínimo 25%

    # ─── Prima de Antigüedad ──────────────────────────────────────────
    PRIMA_ANTIGUEDAD_DIAS_POR_ANO = 12     # 12 días por año

    # ─── Indemnización ────────────────────────────────────────────────
    INDEMNIZACION_DIAS = 90                # 3 meses = 90 días

    @classmethod
    def obtener_tope_salarial(cls) -> Decimal:
        """Calcula el tope salarial para prima de antigüedad."""
        if cls.TOPE_PRIMA_ANTIGUEDAD_TIPO == 'uma':
            return cls.UMA_DIARIA * cls.TOPE_PRIMA_ANTIGUEDAD_MULTIPLO
        elif cls.TOPE_PRIMA_ANTIGUEDAD_TIPO == 'frontera':
            return cls.SALARIO_MINIMO_FRONTERA * cls.TOPE_PRIMA_ANTIGUEDAD_MULTIPLO
        else:
            return cls.SALARIO_MINIMO * cls.TOPE_PRIMA_ANTIGUEDAD_MULTIPLO
