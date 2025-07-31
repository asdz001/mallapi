# ========================================
# 📁 파일 위치: shop/templatetags/table_filters.py
# 🎯 목적: 테이블에서 사용할 커스텀 필터들
# ========================================

from django import template
from django.utils.safestring import mark_safe
from decimal import Decimal

# Django 템플릿 필터를 등록하기 위한 설정
register = template.Library()

@register.filter
def get_field_value(obj, field_config):
    """
    🎯 목적: 객체에서 설정에 따라 필드값을 가져오는 필터
    
    📝 사용법: {{ product|get_field_value:column }}
    
    ⚙️ 처리 과정:
    1. 필드 타입에 따라 다른 방식으로 값을 가져옴
    2. 포맷팅 규칙 적용
    3. 기본값 처리
    """
    field_name = field_config['field']
    field_type = field_config.get('type', 'text')
    default_value = field_config.get('default', '-')
    
    try:
        # 🔧 커스텀 필드 처리 (특별한 로직이 필요한 경우)
        if field_name == 'category_combined':
            # 카테고리1과 카테고리2를 결합해서 표시
            cat1 = getattr(obj, 'category1', '') or ''
            cat2 = getattr(obj, 'category2', '') or ''
            if cat1 and cat2:
                value = f"{cat1} / {cat2}"
            elif cat1:
                value = cat1
            else:
                value = default_value
        else:
            # 🔧 일반 필드 값 가져오기
            value = getattr(obj, field_name, None)
        
        # 🔧 값이 없을 때 기본값 사용
        if value is None or value == '':
            return default_value
        
        # 🔧 필드 타입별 포맷팅 처리
        if field_type == 'choice':
            # 선택지 필드 (예: status)
            display_method = f"get_{field_name}_display"
            if hasattr(obj, display_method):
                return getattr(obj, display_method)()
            return value
            
        elif field_type == 'currency':
            # 통화 필드 (가격 등)
            if isinstance(value, (int, float, Decimal)):
                format_option = field_config.get('format', '2')
                if format_option == '0':
                    return f"{value:,.0f}"  # 소수점 없이
                else:
                    return f"{value:,.2f}"  # 소수점 2자리
            return str(value)
            
        elif field_type == 'date':
            # 날짜 필드
            date_format = field_config.get('format', 'Y-m-d')
            if hasattr(value, 'strftime'):
                return value.strftime('%Y-%m-%d' if date_format == 'Y-m-d' else date_format)
            return str(value)
            
        elif field_type == 'image':
            # 이미지 필드
            if value:
                return mark_safe(f'<img src="{value}" width="60" height="60" class="img-thumbnail">')
            return default_value
            
        elif field_type == 'number':
            # 숫자 필드
            if isinstance(value, (int, float)):
                return f"{value:,}"  # 천단위 콤마
            return str(value)
            
        else:
            # 텍스트 필드 (기본)
            return str(value)
            
    except Exception as e:
        # 오류 발생 시 기본값 반환
        return default_value

@register.filter
def truncate_smart(value, config):
    """
    🎯 목적: 텍스트를 스마트하게 자르는 필터
    
    📝 사용법: {{ text|truncate_smart:column_config }}
    
    ⚙️ 처리 과정:
    1. 설정에서 truncate 길이 확인
    2. 길이가 초과하면 ...으로 자름
    3. multiline 설정 확인하여 CSS 클래스 적용
    """
    if not value:
        return value
    
    truncate_length = config.get('truncate')
    is_multiline = config.get('multiline', False)
    
    # 자르기 길이가 설정되어 있고, 텍스트가 그보다 길면 자르기
    if truncate_length and len(str(value)) > truncate_length:
        truncated = str(value)[:truncate_length] + '...'
        
        # 여러 줄 허용인 경우 특별한 CSS 클래스 적용
        if is_multiline:
            return mark_safe(f'<span class="multiline-text" title="{value}">{truncated}</span>')
        else:
            return mark_safe(f'<span class="text-truncate-custom" title="{value}">{truncated}</span>')
    
    # 자르지 않는 경우
    if is_multiline:
        return mark_safe(f'<span class="multiline-text">{value}</span>')
    
    return value

@register.filter
def get_column_class(config):
    """
    🎯 목적: 컬럼 설정에 따라 CSS 클래스를 생성하는 필터
    
    📝 사용법: {{ column_config|get_column_class }}
    
    🎨 생성되는 CSS 클래스들:
    - text-center, text-left, text-right (정렬)
    - col-fixed-width (고정 너비)
    - truncate-col (자르기가 필요한 컬럼)
    """
    classes = []
    
    # 정렬 클래스
    align = config.get('align', 'left')
    if align == 'center':
        classes.append('text-center')
    elif align == 'right':
        classes.append('text-right')
    
    # 고정 너비 클래스
    if config.get('width'):
        classes.append('col-fixed-width')
    
    # 자르기 클래스
    if config.get('truncate'):
        classes.append('truncate-col')
    
    return ' '.join(classes)