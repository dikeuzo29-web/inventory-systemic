from django import template
from decimal import Decimal
from django.db.models import Sum

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

@register.filter
def aggregate_sum(queryset, field_name):
    """
    Returns the sum of a given field for any queryset.
    Example: sale.items.all|aggregate_sum:'subtotal'
    """
    return queryset.aggregate(total=Sum(field_name))['total'] or 0