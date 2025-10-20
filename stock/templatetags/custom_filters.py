from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def sum_field(objects, field_name):
    return sum(getattr(obj, field_name, 0) for obj in objects)

@register.filter
def mul(value, arg):
    try:
        return Decimal(value) * Decimal(arg)
    except (ValueError, TypeError):
        return Decimal(0) # Return 0 or handle error appropriately if conversion fails
