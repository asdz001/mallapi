# mall_settings/templatetags/operator_extras.py

from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    """딕셔너리에서 key에 해당하는 값을 가져오는 템플릿 필터"""
    return dictionary.get(key, '')
