from django import template

register = template.Library()


@register.filter
def dict_get(obj, key):
    return obj.get(key)
