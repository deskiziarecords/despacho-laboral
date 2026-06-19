"""
Módulo de Cálculos Laborales - Motor Jurídico Parametrizable
============================================================

Arquitectura desacoplada para que las leyes puedan cambiar sin tocar código:
    rules.py      → Tablas legales y constantes configurables (días vacaciones, UMA, SML)
    formulas.py   → Fórmulas matemáticas puras (sin dependencias de Django)
    calculators.py → Orquestadores que combinan datos del expediente + reglas + fórmulas

Las reglas legales se sobreescriben desde LegalConfig en la base de datos.
"""
