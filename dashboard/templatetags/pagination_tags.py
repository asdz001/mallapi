# ========================================
# 📁 파일 위치: shop/templatetags/pagination_tags.py
# 🎯 목적: 페이지네이션을 위한 템플릿 태그
# ========================================

from django import template
from django.http import QueryDict

register = template.Library()

@register.filter
def split(value, delimiter=','):
    """
    문자열을 구분자로 나누는 필터
    
    사용법: {{ "10,25,50,100"|split:"," }}
    """
    if not value:
        return []
    return [item.strip() for item in value.split(delimiter)]

@register.simple_tag
def url_replace(request, **kwargs):
    """
    현재 URL의 파라미터를 유지하면서 특정 파라미터만 변경
    
    사용법: {% url_replace request page=2 %}
    """
    query = request.GET.copy()
    for key, value in kwargs.items():
        if value is not None:
            query[key] = value
        else:
            query.pop(key, None)
    return query.urlencode()

@register.inclusion_tag('common/pagination.html', takes_context=True)
def render_pagination(context, items, **kwargs):
    """
    페이지네이션을 렌더링하는 포함 태그
    
    사용법: 
    {% render_pagination items %}
    {% render_pagination items per_page_options="10,25,50" %}
    {% render_pagination items sort_choices=sort_choices %}
    """
    request = context['request']
    
    # 기본값 설정
    per_page_options = kwargs.get('per_page_options', [10, 25, 50, 100])
    sort_choices = kwargs.get('sort_choices', None)
    
    # 현재 값들 가져오기
    current_per_page = int(request.GET.get('per_page', 25))
    current_sort = request.GET.get('sort', '')
    
    return {
        'items': items,
        'request': request,
        'per_page_options': per_page_options,
        'sort_choices': sort_choices,
        'per_page': current_per_page,
        'sort_by': current_sort,
    }

@register.simple_tag
def page_url(request, page_num):
    """
    특정 페이지 번호로 이동하는 URL 생성
    
    사용법: {% page_url request 2 %}
    """
    query = request.GET.copy()
    query['page'] = page_num
    return f"?{query.urlencode()}"

@register.simple_tag  
def get_page_range(paginator, current_page, window=3):
    """
    현재 페이지 주변의 페이지 범위를 계산
    
    사용법: {% get_page_range items.paginator items.number %}
    """
    start = max(1, current_page - window)
    end = min(paginator.num_pages + 1, current_page + window + 1)
    return range(start, end)