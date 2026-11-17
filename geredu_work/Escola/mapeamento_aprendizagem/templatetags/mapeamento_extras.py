from django import template

register = template.Library()

@register.filter
def get_item(mapping, key):
    return mapping.get(key) if mapping else None

@register.filter
def get_field(obj, name):
    return getattr(obj, name, "") if obj else ""
