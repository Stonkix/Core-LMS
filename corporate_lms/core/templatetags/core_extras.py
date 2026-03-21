from django import template

register = template.Library()

@register.filter
def lookup(d, key):
    """Позволяет делать dict|lookup:key в шаблонах"""
    if isinstance(d, dict):
        return d.get(key)
    return None