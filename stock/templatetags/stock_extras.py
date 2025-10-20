from django import template

register = template.Library()

@register.simple_tag
def querystring(request, **kwargs):
    query = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            if key in query:
                del query[key]
        else:
            query[key] = value
    return query.urlencode()
