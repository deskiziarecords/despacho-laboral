import re
from django import template

register = template.Library()


@register.filter(name='intcomma')
def intcomma(value):
    """Convierte un número a formato con separadores de miles (ej: 1234567 -> 1.234.567)."""
    if value is None:
        return '0'
    try:
        if isinstance(value, float):
            value = int(value)
        s = str(value)
        result = re.sub(r'(\d)(?=(\d{3})+(?!\d))', r'\1.', s)
        return result
    except (ValueError, TypeError):
        return str(value)


@register.filter(name='get_item')
def get_item(dictionary, key):
    """Obtiene un valor de un diccionario por clave."""
    return dictionary.get(key, '')


@register.filter(name='div')
def divide(value, arg):
    """Divide value por arg. Para calcular porcentajes en templates."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0


@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplica value por arg. Para calcular porcentajes en templates."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
