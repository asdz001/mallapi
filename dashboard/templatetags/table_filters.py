# dashboard/templatetags/table_filters.py
# 기존 파일에 품절상태 처리 기능 추가

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter
def get_column_class(column):
    """컬럼 설정에 따른 CSS 클래스 반환"""
    classes = []
    
    # 정렬 설정
    if column.get('align'):
        if column['align'] == 'center':
            classes.append('text-center')
        elif column['align'] == 'right':
            classes.append('text-right')
        elif column['align'] == 'left':
            classes.append('text-left')
    
    # 타입별 클래스
    if column.get('type') == 'currency':
        classes.append('text-right')
    elif column.get('type') == 'number':
        classes.append('text-right')
    elif column.get('type') == 'date':
        classes.append('text-center')
    
    return ' '.join(classes)


@register.filter
def get_field_value(obj, column):
    """객체에서 필드 값을 가져오고 포맷팅"""
    field_name = column['field']
    field_type = column.get('type', 'text')
    default_value = column.get('default', '-')
    
    try:
        # 🆕 계산된 필드 처리 (품절상태)
        if field_name == 'sold_out_status':
            # annotate로 추가된 필드이므로 직접 접근
            if hasattr(obj, 'sold_out_status'):
                return obj.sold_out_status
            else:
                # 백업 로직: 직접 계산
                if hasattr(obj, 'status') and obj.status == 'sold_out':
                    return 'sold_out'
                elif hasattr(obj, 'total_stock') and obj.total_stock == 0:
                    return 'sold_out'
                else:
                    return 'available'
        
        # 🆕 옵션 재고 합계 처리
        elif field_name == 'options_total_stock':
            if hasattr(obj, 'total_stock'):
                return obj.total_stock
            else:
                # 백업: 옵션 재고 직접 계산
                try:
                    total = sum(option.stock for option in obj.options.all())
                    return total
                except:
                    return 0
        
        # 🆕 커스텀 필드 처리
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
        
        # 일반 필드 처리
        else:
            # 점표기법 지원 (예: 'user.username')
            if '.' in field_name:
                value = obj
                for attr in field_name.split('.'):
                    value = getattr(value, attr, None)
                    if value is None:
                        break
            else:
                value = getattr(obj, field_name, None)
        
        # None 값 처리
        if value is None:
            return default_value
        
        # 타입별 포맷팅
        return format_field_value(value, field_type, column)
        
    except (AttributeError, TypeError):
        return default_value


def format_field_value(value, field_type, column):
    """필드 타입에 따른 값 포맷팅"""
    
    if field_type == 'currency':
        try:
            # 통화 포맷팅
            format_option = column.get('format', '2')
            if format_option == '0':
                return f"{float(value):,.0f}"
            else:
                return f"{float(value):,.2f}"
        except (ValueError, TypeError):
            return column.get('default', '-')
    
    elif field_type == 'number':
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return column.get('default', '0')
    
    elif field_type == 'decimal':
        try:
            return f"{float(value):.2f}"
        except (ValueError, TypeError):
            return column.get('default', '-')
    
    elif field_type == 'date':
        try:
            if hasattr(value, 'strftime'):
                date_format = column.get('format', 'Y-m-d')
                # Django 스타일 날짜 포맷을 Python 스타일로 변환
                python_format = date_format.replace('Y', '%Y').replace('m', '%m').replace('d', '%d').replace('H', '%H').replace('i', '%M')
                return value.strftime(python_format)
            else:
                return str(value)
        except (ValueError, AttributeError):
            return column.get('default', '-')
    
    elif field_type == 'choice':
        # Django 모델의 get_FOO_display() 메서드 활용
        try:
            if hasattr(value, '_state'):  # Django 모델 객체인 경우
                display_method = f"get_{column['field']}_display"
                if hasattr(value, display_method):
                    return getattr(value, display_method)()
            return str(value)
        except:
            return str(value)
    
    elif field_type == 'image':
        # 이미지 썸네일 생성
        if value:
            return format_html(
                '<img src="{}" class="img-thumbnail" style="max-width: 50px; max-height: 50px;" onerror="this.src=\'/static/images/no-image.png\'">',
                value
            )
        else:
            return format_html('<span class="text-muted">이미지없음</span>')
    
    elif field_type == 'sold_out_badge':
        # 🆕 품절상태 배지 처리
        if value == 'sold_out':
            return format_html('<span class="badge badge-danger">품절됨</span>')
        else:
            return format_html('<span class="badge badge-success">판매중</span>')
    
    elif field_type == 'fta_badge':
        # FTA 적용 배지 (원산지 관리에서 사용)
        if value:
            return format_html('<span class="badge badge-success">적용</span>')
        else:
            return format_html('<span class="badge badge-secondary">미적용</span>')
    
    elif field_type == 'count_badge':
        # 개수 배지
        try:
            count = int(value)
            if count > 0:
                return format_html('<span class="badge badge-info">{}</span>', count)
            else:
                return format_html('<span class="badge badge-light">0</span>')
        except (ValueError, TypeError):
            return format_html('<span class="badge badge-light">0</span>')
    
    elif field_type == 'code_text':
        # 코드 스타일 텍스트
        return format_html('<code>{}</code>', value)
    
    else:
        # 기본 텍스트 처리
        return str(value) if value is not None else column.get('default', '-')


@register.filter
def truncate_smart(value, column):
    """스마트 텍스트 자르기 (multiline 지원)"""
    if not value:
        return column.get('default', '-')
    
    value_str = str(value)
    truncate_length = column.get('truncate')
    is_multiline = column.get('multiline', False)
    
    if not truncate_length:
        return value_str
    
    if len(value_str) <= truncate_length:
        return value_str
    
    # 자르기 처리
    truncated = value_str[:truncate_length]
    
    if is_multiline:
        # 멀티라인인 경우 CSS 클래스 추가
        return format_html(
            '<span class="multiline-text" title="{}">{}&hellip;</span>',
            value_str,
            truncated
        )
    else:
        # 한 줄인 경우
        return format_html(
            '<span class="text-truncate-custom" title="{}">{}&hellip;</span>',
            value_str,
            truncated
        )


@register.filter
def format_status_badge(status):
    """상품 상태를 배지로 표시"""
    status_config = {
        'draft': {'label': '미등록', 'class': 'secondary'},
        'published': {'label': '등록', 'class': 'primary'},
        'sold_out': {'label': '품절됨', 'class': 'danger'},
        'discontinued': {'label': '단종', 'class': 'dark'},
    }
    
    config = status_config.get(status, {'label': status, 'class': 'light'})
    
    return format_html(
        '<span class="badge badge-{}">{}</span>',
        config['class'],
        config['label']
    )


@register.filter
def format_stock_status(stock):
    """재고 상태를 색상으로 표시"""
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
    """정렬 아이콘 표시"""
    if current_sort == field_name:
        return format_html('<i class="fas fa-sort-up text-primary"></i>')
    elif current_sort == f'-{field_name}':
        return format_html('<i class="fas fa-sort-down text-primary"></i>')
    else:
        return format_html('<i class="fas fa-sort text-muted"></i>')


@register.filter
def add_class(field, css_class):
    """폼 필드에 CSS 클래스 추가"""
    return field.as_widget(attrs={'class': css_class})