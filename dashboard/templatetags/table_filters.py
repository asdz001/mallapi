# dashboard/templatetags/table_filters.py
"""
========================================
📁 파일 위치: dashboard/templatetags/table_filters.py
🎯 목적: 테이블 동적 생성을 위한 Template Filter 모음
📅 버전: 2.0 - 오류 수정 및 주석 추가
========================================

사용 방법:
1. HTML에서 {% load table_filters %} 선언
2. {{ object|get_field_value:column }} 형태로 사용
3. 컬럼 설정은 views.py에서 COLUMNS 배열로 정의

지원하는 필드 타입:
- text: 일반 텍스트
- currency: 통화 (1,234.56)
- number: 숫자 (1,234)
- date: 날짜 (2024-01-15)
- image: 이미지 썸네일
- choice: Django 모델 선택 필드
- sold_out_badge: 품절상태 배지
- custom: 사용자 정의 필드
"""

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import re

register = template.Library()

# ========================================
# 🎨 CSS 클래스 관련 필터
# ========================================

@register.filter
def get_column_class(column):
    """
    컬럼 설정에 따른 CSS 클래스 생성
    
    Args:
        column (dict): 컬럼 설정 딕셔너리
            - align: 'left', 'center', 'right'
            - type: 'currency', 'number', 'date' 등
    
    Returns:
        str: CSS 클래스 문자열
    
    사용 예시:
        <td class="{{ column|get_column_class }}">
    """
    classes = []
    
    # 🔧 정렬 클래스 추가
    align = column.get('align', '')
    if align == 'center':
        classes.append('text-center')
    elif align == 'right':
        classes.append('text-right')
    elif align == 'left':
        classes.append('text-left')
    
    # 🔧 타입별 기본 클래스 추가
    field_type = column.get('type', 'text')
    if field_type in ['currency', 'number', 'decimal']:
        classes.append('text-right')  # 숫자는 우측 정렬
    elif field_type == 'date':
        classes.append('text-center')  # 날짜는 중앙 정렬
    
    # 🔧 고정 너비 컬럼 처리
    if column.get('width'):
        classes.append('col-fixed-width')
    
    return ' '.join(classes)

# ========================================
# 📊 필드 값 추출 및 포맷팅
# ========================================

@register.filter
def get_field_value(obj, column):
    """
    객체에서 필드 값을 추출하고 타입에 맞게 포맷팅
    
    Args:
        obj: Django 모델 객체 (Product, Member 등)
        column (dict): 컬럼 설정
            - field: 필드명 ('product_name', 'user.username' 등)
            - type: 필드 타입 ('text', 'currency', 'date' 등)
            - default: 기본값 (값이 없을 때 표시)
    
    Returns:
        str/SafeString: 포맷팅된 값
    
    사용 예시:
        {{ product|get_field_value:column }}
    """
    field_name = column['field']
    field_type = column.get('type', 'text')
    default_value = column.get('default', '-')
    
    try:
        # 🔧 특수 계산 필드 처리
        value = _get_special_field_value(obj, field_name, default_value)
        
        if value is not None:
            return format_field_value(value, field_type, column)
        
        # 🔧 일반 필드 처리
        value = _extract_field_value(obj, field_name)
        
        # None 값 처리
        if value is None:
            return default_value
        
        # 타입별 포맷팅 적용
        return format_field_value(value, field_type, column)
        
    except (AttributeError, TypeError, ValueError) as e:
        # 오류 발생 시 기본값 반환 (운영에서는 로그 기록 권장)
        # print(f"Field extraction error: {field_name}, {e}")  # 디버깅용
        return default_value

def _get_special_field_value(obj, field_name, default_value):
    """
    특수 계산이 필요한 필드 값 처리
    
    Args:
        obj: 모델 객체
        field_name: 필드명
        default_value: 기본값
    
    Returns:
        계산된 값 또는 None (일반 필드인 경우)
    """
    
    # 🆕 품절상태 계산 (비즈니스 로직)
    if field_name == 'sold_out_status':
        # 1순위: status 필드 확인
        if hasattr(obj, 'status') and obj.status == 'soldout':
            return 'soldout'
        # 2순위: 재고 확인 (annotate된 필드 또는 @property)
        elif hasattr(obj, 'sold_out_status'):
            return obj.sold_out_status  # annotate로 추가된 필드
        elif hasattr(obj, 'total_stock') and obj.total_stock == 0:
            return 'soldout'
        else:
            return 'available'
    
    # 🔧 재고 합계 처리 (Product.total_stock @property 사용)
    elif field_name == 'total_stock':
        if hasattr(obj, 'total_stock'):
            return obj.total_stock  # @property 메서드 호출
        else:
            # 백업: 직접 계산 (성능상 권장하지 않음)
            try:
                return sum(option.stock for option in obj.options.all())
            except AttributeError:
                return 0
    
    # 🔧 카테고리 결합 표시
    elif field_name == 'category_combined':
        category1 = getattr(obj, 'category1', '') or ''
        category2 = getattr(obj, 'category2', '') or ''
        
        if category1 and category2:
            return f"{category1} > {category2}"
        elif category1:
            return category1
        elif category2:
            return category2
        else:
            return default_value
    
    # 🔧 마크업 계산 (가격 관련)
    elif field_name == 'markup_percentage':
        try:
            cost = getattr(obj, 'price_org', 0) or 0
            retail = getattr(obj, 'price_retail', 0) or 0
            if cost > 0:
                markup = ((retail - cost) / cost) * 100
                return f"{markup:.1f}%"
            else:
                return default_value
        except (ZeroDivisionError, TypeError):
            return default_value
    
    # 🔧 상품 상태별 진열 여부 (판매상태)
    elif field_name == 'display_status':
        status = getattr(obj, 'status', '')
        if status in ['active', 'soldout']:
            return 'displayed'  # 진열됨
        else:
            return 'not_displayed'  # 미진열
    
    # 일반 필드인 경우 None 반환
    return None

def _extract_field_value(obj, field_name):
    """
    객체에서 필드 값 추출 (점표기법 지원)
    
    Args:
        obj: 모델 객체
        field_name: 필드명 ('name' 또는 'user.username' 형태)
    
    Returns:
        추출된 값 또는 None
    
    사용 예시:
        user.profile.name → obj.user.profile.name 접근
    """
    
    # 점표기법 지원 (관계 필드 접근)
    if '.' in field_name:
        value = obj
        for attr in field_name.split('.'):
            if value is None:
                break
            value = getattr(value, attr, None)
        return value
    else:
        # 단일 필드 접근
        return getattr(obj, field_name, None)

# ========================================
# 🎨 타입별 포맷팅 함수
# ========================================

def format_field_value(value, field_type, column):
    """
    필드 타입에 따른 값 포맷팅
    
    Args:
        value: 원본 값
        field_type: 필드 타입 ('currency', 'date', 'image' 등)
        column: 컬럼 설정 (format 옵션 등)
    
    Returns:
        SafeString: 포맷팅된 HTML 결과
    """
    
    # 🔧 통화 포맷팅 (1,234.56 형태)
    if field_type == 'currency':
        try:
            format_option = column.get('format', '2')
            if format_option == '0':
                return f"{float(value):,.0f}"  # 소수점 없음
            else:
                return f"{float(value):,.2f}"  # 소수점 2자리
        except (ValueError, TypeError):
            return column.get('default', '-')
    
    # 🔧 숫자 포맷팅 (1,234 형태)
    elif field_type == 'number':
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return column.get('default', '0')
    
    # 🔧 소수점 포맷팅 (12.34 형태)
    elif field_type == 'decimal':
        try:
            decimal_places = column.get('decimal_places', 2)
            return f"{float(value):.{decimal_places}f}"
        except (ValueError, TypeError):
            return column.get('default', '-')
    
    # 🔧 날짜 포맷팅
    elif field_type == 'date':
        try:
            if hasattr(value, 'strftime'):
                # Django 스타일 → Python 스타일 변환
                date_format = column.get('format', 'Y-m-d')
                python_format = (date_format.replace('Y', '%Y')
                                          .replace('m', '%m')
                                          .replace('d', '%d')
                                          .replace('H', '%H')
                                          .replace('i', '%M')
                                          .replace('s', '%S'))
                return value.strftime(python_format)
            else:
                return str(value)
        except (ValueError, AttributeError):
            return column.get('default', '-')
    
    # 🔧 Django 모델 선택 필드 (get_FOO_display 활용)
    elif field_type == 'choice':
        try:
            # 모델 객체에서 display 메서드 찾기
            if hasattr(value, '_state'):  # Django 모델 객체인 경우
                display_method = f"get_{column['field']}_display"
                if hasattr(value, display_method):
                    return getattr(value, display_method)()
            return str(value)
        except AttributeError:
            return str(value)
    
    # 🔧 이미지 썸네일 생성
    elif field_type == 'image':
        if value:
            max_width = column.get('image_width', '50px')
            max_height = column.get('image_height', '50px')
            return format_html(
                '<img src="{}" class="img-thumbnail" '
                'style="max-width: {}; max-height: {}; object-fit: cover;" '
                'onerror="this.src=\'/static/images/no-image.png\'" '
                'alt="상품 이미지">',
                value, max_width, max_height
            )
        else:
            return format_html('<span class="text-muted">이미지없음</span>')
    
    # 🆕 품절상태 배지 (비즈니스 로직 반영)
    elif field_type == 'sold_out_badge':
        if value == 'soldout':
            return format_html('<span class="badge badge-danger">품절됨</span>')
        else:
            return format_html('<span class="badge badge-success">판매중</span>')
    
    # 🔧 상품 상태 배지
    elif field_type == 'status_badge':
        status_config = {
            'pending': {'label': '미등록', 'class': 'secondary'},
            'active': {'label': '등록됨', 'class': 'primary'},
            'soldout': {'label': '품절됨', 'class': 'danger'},
            'discontinued': {'label': '단종', 'class': 'dark'},
        }
        config = status_config.get(value, {'label': str(value), 'class': 'light'})
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            config['class'], config['label']
        )
    
    # 🔧 FTA 적용 여부 배지 (원산지 관리용)
    elif field_type == 'fta_badge':
        if value:
            return format_html('<span class="badge badge-success">적용</span>')
        else:
            return format_html('<span class="badge badge-secondary">미적용</span>')
    
    # 🔧 개수 배지 (별칭 개수 등)
    elif field_type == 'count_badge':
        try:
            count = int(value)
            if count > 0:
                return format_html('<span class="badge badge-info">{}</span>', count)
            else:
                return format_html('<span class="badge badge-light">0</span>')
        except (ValueError, TypeError):
            return format_html('<span class="badge badge-light">0</span>')
    
    # 🔧 코드 스타일 텍스트 (원산지명 등)
    elif field_type == 'code_text':
        return format_html('<code class="text-muted">{}</code>', value)
    
    # 🔧 링크 형태
    elif field_type == 'link':
        url = column.get('url', '#')
        return format_html('<a href="{}" target="_blank">{}</a>', url, value)
    
    # 🔧 기본 텍스트 처리
    else:
        return str(value) if value is not None else column.get('default', '-')

# ========================================
# 🔧 텍스트 자르기 및 표시 옵션
# ========================================

@register.filter
def truncate_smart(value, column):
    """
    스마트 텍스트 자르기 (multiline 지원)
    
    Args:
        value: 원본 텍스트
        column: 컬럼 설정
            - truncate: 자를 글자 수
            - multiline: 여러 줄 표시 여부
    
    Returns:
        SafeString: 자른 텍스트 + CSS 클래스
    
    사용 예시:
        {{ field_value|truncate_smart:column }}
    """
    if not value:
        return column.get('default', '-')
    
    value_str = str(value)
    truncate_length = column.get('truncate')
    is_multiline = column.get('multiline', False)
    
    # 자르기 길이가 설정되지 않았거나 이미 짧은 경우
    if not truncate_length or len(value_str) <= truncate_length:
        return value_str
    
    # 자르기 처리
    truncated = value_str[:truncate_length]
    
    if is_multiline:
        # 멀티라인: 최대 2줄까지 표시
        return format_html(
            '<span class="multiline-text" title="{}" data-toggle="tooltip">{}&hellip;</span>',
            value_str.replace('"', '&quot;'),  # HTML 속성 안전 처리
            truncated
        )
    else:
        # 한 줄: 말줄임표 처리
        return format_html(
            '<span class="text-truncate-custom" title="{}" data-toggle="tooltip">{}&hellip;</span>',
            value_str.replace('"', '&quot;'),
            truncated
        )

# ========================================
# 🎨 추가 포맷팅 필터들
# ========================================

@register.filter
def format_stock_status(stock):
    """
    재고 수량에 따른 색상 표시
    
    Args:
        stock: 재고 수량
    
    Returns:
        SafeString: 색상이 적용된 재고 표시
    """
    try:
        stock_num = int(stock)
        if stock_num == 0:
            return format_html('<span class="text-danger font-weight-bold">{}</span>', stock)
        elif stock_num <= 5:
            return format_html('<span class="text-warning font-weight-bold">{}</span>', stock)
        else:
            return format_html('<span class="text-success">{}</span>', stock)
    except (ValueError, TypeError):
        return str(stock)

@register.simple_tag
def get_sort_icon(current_sort, field_name):
    """
    정렬 아이콘 표시 (테이블 헤더용)
    
    Args:
        current_sort: 현재 정렬 상태 ('name', '-name' 등)
        field_name: 필드명
    
    Returns:
        SafeString: 정렬 아이콘 HTML
    
    사용 예시:
        <th>상품명 {% get_sort_icon sort_by 'product_name' %}</th>
    """
    if current_sort == field_name:
        return format_html('<i class="fas fa-sort-up text-primary"></i>')
    elif current_sort == f'-{field_name}':
        return format_html('<i class="fas fa-sort-down text-primary"></i>')
    else:
        return format_html('<i class="fas fa-sort text-muted"></i>')

@register.filter
def add_class(field, css_class):
    """
    Django 폼 필드에 CSS 클래스 추가
    
    Args:
        field: Django 폼 필드
        css_class: 추가할 CSS 클래스
    
    Returns:
        폼 필드 HTML (클래스 추가됨)
    
    사용 예시:
        {{ form.name|add_class:"form-control" }}
    """
    return field.as_widget(attrs={'class': css_class})

# ========================================
# 🔧 유틸리티 필터
# ========================================

@register.filter
def get_item(dictionary, key):
    """
    딕셔너리에서 동적 키로 값 가져오기
    
    Args:
        dictionary: 딕셔너리 객체
        key: 키 값
    
    Returns:
        딕셔너리 값
    
    사용 예시:
        {{ settings|get_item:column.field }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def multiply(value, arg):
    """
    곱셈 연산 (템플릿에서 계산용)
    
    Args:
        value: 첫 번째 숫자
        arg: 두 번째 숫자
    
    Returns:
        곱셈 결과
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """
    백분율 계산
    
    Args:
        value: 부분 값
        total: 전체 값
    
    Returns:
        백분율 문자열 (12.5%)
    """
    try:
        if float(total) == 0:
            return "0%"
        return f"{(float(value) / float(total) * 100):.1f}%"
    except (ValueError, TypeError, ZeroDivisionError):
        return "0%"