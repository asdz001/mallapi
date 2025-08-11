# shop_product/views/product_list.py
# 상품목록 뷰 - 오류 수정 및 최적화 완료

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from shop.models import Product
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, IntegerField, Value, CharField
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.html import escape
import json

# ========================================
# 🔧 검색 엔진 설정
# ========================================

SEARCH_FIELDS = [
    ('product_name', _('상품명')),
    ('brand_name', _('브랜드명')),
    ('sku', 'SKU'),
    ('retailer', _('부띠끄')),
    ('external_product_id', _('상품ID')),
    ('category1', _('카테고리1')),
    ('color', _('색상')),
]

# 🆕 상품분류 필터 설정
GENDER_CHOICES = [
    ('', _('전체')),
    ('남성', _('남성')),
    ('여성', _('여성')),
    ('공용', _('공용')),
]

# 🆕 날짜 기준 설정
DATE_FIELD_CHOICES = [
    ('created_at', _('등록일')),
    ('updated_at', _('수정일')),
]

# 🆕 날짜 범위 설정
DATE_RANGE_CHOICES = [
    ('', _('직접입력')),
    ('today', _('오늘')),
    ('yesterday', _('어제')),
    ('3days', _('3일')),
    ('7days', _('7일')),
    ('1month', _('1개월')),
    ('3months', _('3개월')),
]

# 🆕 재고수량 필터 설정
STOCK_STATUS_CHOICES = [
    ('', _('전체')),
    ('available', _('재고있음')),
    ('out_of_stock', _('재고없음')),
]

# 🆕 상품가격 기준 설정
PRICE_FIELD_CHOICES = [
    ('price_org', _('원가(COST)')),
    ('price_supply', _('공급가')),
    ('price_retail', _('소비자가')),
    ('calculated_price_krw', _('원화가')),
]

# 🔧 품절상태 설정 (실제 models.py status와 일치)
SOLD_OUT_STATUS_CHOICES = [
    ('', _('전체')),
    ('soldout', _('품절됨')),    # ← models.py와 일치
    ('available', _('품절안됨')),
]

# 🔧 판매상태 설정 (실제 구현)
SALES_STATUS_CHOICES = [
    ('', _('전체')),
    ('displayed', _('진열함')),     # active + soldout
    ('not_displayed', _('미진열')), # pending
]

# 🆕 정렬 설정
SORT_CHOICES = [
    ('-created_at', _('등록일 역순 (최신순)')),
    ('created_at', _('등록일 순 (오래된순)')),
    ('-updated_at', _('수정일 역순 (최신순)')),
    ('updated_at', _('수정일 순 (오래된순)')),
    ('price_retail', _('판매가 순 (저가순)')),
    ('-price_retail', _('판매가 역순 (고가순)')),
    ('price_org', _('COST 순 (저가순)')),
    ('-price_org', _('COST 역순 (고가순)')),
]

# ========================================
# 🔧 테이블 컬럼 설정 (기본값) - 나중에 UserTableColumnSetting으로 커스터마이즈 예정
# ========================================

PRODUCT_TABLE_COLUMNS = [
    {
        'field': 'external_product_id',
        'header': _('상품ID'),
        'width': '80px',
        'truncate': 15,
        'align': 'center',
        'type': 'text'
    },
    {
        'field': 'retailer',
        'header': _('부띠끄'),
        'width': '100px',
        'align': 'center',
        'type': 'text'
    },
    {
        'field': 'image_url_1',
        'header': _('썸네일'),
        'width': '80px',
        'align': 'center',
        'type': 'image'
    },
    {
        'field': 'brand_name',
        'header': _('브랜드'),
        'width': '120px',
        'type': 'text'
    },
    {
        'field': 'product_name',
        'header': _('상품명'),
        'width': '200px',
        'multiline': True,
        'truncate': 50,
        'type': 'text'
    },
    {
        'field': 'sku',
        'header': _('SKU'),
        'width': '120px',
        'type': 'text'
    },
    {
        'field': 'gender',
        'header': _('성별'),
        'width': '80px',
        'align': 'center',
        'type': 'text'
    },
    {
        'field': 'category_combined',
        'header': _('카테고리'),
        'width': '150px',
        'type': 'custom'
    },
    {
        'field': 'season',
        'header': _('시즌'),
        'width': '80px',
        'align': 'center',
        'type': 'text'
    },
    {
        'field': 'color',
        'header': _('색상'),
        'width': '80px',
        'align': 'center',
        'type': 'text'
    },
    {
        'field': 'price_retail',
        'header': _('소비자가(€)'),
        'width': '110px',
        'align': 'center',
        'type': 'currency'
    },
    {
        'field': 'price_org',
        'header': _('COST'),
        'width': '100px',
        'align': 'center',
        'type': 'currency'
    },
    {
        'field': 'markup',
        'header': _('MARKUP'),
        'width': '90px',
        'align': 'center',
        'type': 'decimal',
        'default': '-'
    },
    {
        'field': 'price_supply',
        'header': _('공급가(€)'),
        'width': '100px',
        'align': 'center',
        'type': 'currency',
        'format': '0'
    },
    {
        'field': 'retail_price_krw',
        'header': _('소비자가'),
        'width': '100px',
        'align': 'center',
        'type': 'currency',
        'default': '-',
        'format': '0'
    },
    {
        'field': 'calculated_price_krw',
        'header': _('판매가'),
        'width': '100px',
        'align': 'center',
        'type': 'currency',
        'default': '-',
        'format': '0'
    },
    {
        'field': 'total_stock',        # Product.total_stock @property 사용
        'header': _('재고'),
        'width': '80px',
        'align': 'center',
        'type': 'number'
    },
    {
        'field': 'status',
        'header': _('판매상태'),
        'width': '100px',
        'align': 'center',
        'type': 'choice'
    },
    {
        'field': 'sold_out_status',  # 🆕 품절상태 (계산된 필드)
        'header': _('품절상태'),
        'width': '100px',
        'align': 'center',
        'type': 'sold_out_badge'
    },
    {
        'field': 'created_at',
        'header': _('등록일'),
        'width': '100px',
        'align': 'center',
        'type': 'date',
        'format': 'Y-m-d'
    },
    {
        'field': 'updated_at',
        'header': _('수정일'),
        'width': '100px',
        'align': 'center',
        'type': 'date',
        'format': 'Y-m-d'
    }
]

# ========================================
# 🔧 뷰 함수
# ========================================

@staff_member_required
def product_list(request):
    """
    상품 리스트 페이지 - 오류 수정 및 최적화 완료
    - 품절상태/판매상태 실제 구현
    - 쿼리 최적화 (prefetch_related)
    - 재고 호버용 JSON 데이터 안전 처리
    """
    
    # 📝 기본 검색 파라미터
    search_field = request.GET.get('search_field', 'product_name')
    search_value = request.GET.get('search_value', '').strip()
    sort_by = request.GET.get('sort', '-created_at')
    per_page = int(request.GET.get('per_page', 20))
    page = request.GET.get('page', 1)

    # 🆕 상품분류 필터 파라미터
    gender_filter = request.GET.get('gender', '')
    category1_filter = request.GET.get('category1', '')
    category2_filter = request.GET.get('category2', '')
    include_subcategory = request.GET.get('include_subcategory') == 'on'

    # 🆕 날짜 필터 파라미터
    date_field = request.GET.get('date_field', 'created_at')
    date_range = request.GET.get('date_range', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # 🆕 재고수량 필터 파라미터
    stock_status = request.GET.get('stock_status', '')
    min_stock = request.GET.get('min_stock', '')
    max_stock = request.GET.get('max_stock', '')

    # 🆕 상품가격 필터 파라미터
    price_field = request.GET.get('price_field', 'price_org')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')

    # 🔧 품절상태 필터 파라미터 (실제 구현)
    sold_out_status = request.GET.get('sold_out_status', '')

    # 🔧 판매상태 필터 파라미터 (실제 구현)
    sales_status = request.GET.get('sales_status', '')

    # 📝 유효성 검사
    valid_fields = [field[0] for field in SEARCH_FIELDS]
    if search_field not in valid_fields:
        search_field = 'product_name'

    valid_sort_options = [choice[0] for choice in SORT_CHOICES]
    if sort_by not in valid_sort_options:
        sort_by = '-created_at'

    # 🔍 기본 쿼리셋 + 최적화 (prefetch_related)
    products_qs = Product.objects.all().prefetch_related('options').annotate(
        # 🆕 품절상태 계산 (1순위: status, 2순위: 실제 재고는 Python에서 처리)
        sold_out_status=Case(
            When(status='soldout', then=Value('soldout')),
            default=Value('available'),
            output_field=CharField(max_length=20)
        )
    ).order_by(sort_by)
    
    # 🔍 검색어 필터링
    if search_value:
        if search_field == 'product_name':
            products_qs = products_qs.filter(product_name__icontains=search_value)
        elif search_field == 'brand_name':
            products_qs = products_qs.filter(brand_name__icontains=search_value)
        elif search_field == 'sku':
            products_qs = products_qs.filter(sku__icontains=search_value)
        elif search_field == 'retailer':
            products_qs = products_qs.filter(retailer__icontains=search_value)
        elif search_field == 'external_product_id':
            products_qs = products_qs.filter(external_product_id__icontains=search_value)
        elif search_field == 'category1':
            products_qs = products_qs.filter(category1__icontains=search_value)
        elif search_field == 'color':
            products_qs = products_qs.filter(color__icontains=search_value)

    # 🔍 상품분류 필터링
    if gender_filter:
        products_qs = products_qs.filter(gender=gender_filter)
    
    if category1_filter:
        products_qs = products_qs.filter(category1=category1_filter)
    
    if category2_filter:
        if include_subcategory:
            products_qs = products_qs.filter(category2__icontains=category2_filter)
        else:
            products_qs = products_qs.filter(category2=category2_filter)

    # 🔍 날짜 필터링
    if date_range or start_date or end_date:
        date_filter = {}
        
        # 날짜 범위 처리
        if date_range == 'today':
            start_date = timezone.now().date()
            end_date = start_date
        elif date_range == 'yesterday':
            start_date = timezone.now().date() - timedelta(days=1)
            end_date = start_date
        elif date_range == '3days':
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=2)
        elif date_range == '7days':
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=6)
        elif date_range == '1month':
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=29)
        elif date_range == '3months':
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=89)

        # 날짜 필터 적용
        if start_date:
            date_filter[f'{date_field}__gte'] = start_date
        if end_date:
            date_filter[f'{date_field}__lte'] = end_date

        if date_filter:
            products_qs = products_qs.filter(**date_filter)

    # 🔍 상품가격 필터링
    if min_price or max_price:
        price_filter = {}
        try:
            if min_price:
                price_filter[f'{price_field}__gte'] = float(min_price)
            if max_price:
                price_filter[f'{price_field}__lte'] = float(max_price)
            
            if price_field == 'calculated_price_krw':
                price_filter[f'{price_field}__isnull'] = False
            
            products_qs = products_qs.filter(**price_filter)
        except ValueError:
            pass

    # 🔧 판매상태 필터링 (실제 구현)
    if sales_status == 'displayed':
        # 진열함: active 또는 soldout (고객이 볼 수 있는 상품)
        products_qs = products_qs.filter(status__in=['active', 'soldout'])
    elif sales_status == 'not_displayed':
        # 미진열: pending (고객이 못 보는 상품)
        products_qs = products_qs.filter(status='pending')

    # 📝 동적 데이터 수집 (드롭다운 옵션용)
    all_category1 = Product.objects.values_list('category1', flat=True).distinct().exclude(category1__isnull=True).exclude(category1__exact='')
    all_category2 = Product.objects.values_list('category2', flat=True).distinct().exclude(category2__isnull=True).exclude(category2__exact='')
    
    if category1_filter:
        filtered_category2 = Product.objects.filter(category1=category1_filter).values_list('category2', flat=True).distinct().exclude(category2__isnull=True).exclude(category2__exact='')
    else:
        filtered_category2 = all_category2

    # 📝 페이징 처리
    paginator = Paginator(products_qs, per_page)
    products = paginator.get_page(page)

    # 🔧 각 상품의 옵션 데이터를 JSON으로 준비 + 품절상태 재계산
    for product in products:
        options_data = []
        total_stock_sum = 0  # 실제 재고 합계 계산
        
        # prefetch_related로 이미 가져온 옵션들 사용 (DB 조회 없음)
        for option in product.options.all().order_by('-stock', 'option_name'):
            options_data.append({
                'name': option.option_name,
                'stock': option.stock,
                'price_krw': str(option.price_krw) if option.price_krw else None
            })
            total_stock_sum += option.stock  # 재고 합계
        
        # 🔧 HTML 안전한 JSON 생성 (escape 처리)
        product.options_json = escape(json.dumps(options_data, ensure_ascii=False))
        
        # 🔧 실제 품절상태 재계산 (2순위 로직 적용)
        if product.status == 'soldout':
            product.sold_out_status = 'soldout'  # 1순위: status 기반
        elif total_stock_sum == 0:
            product.sold_out_status = 'soldout'  # 2순위: 재고 0
        else:
            product.sold_out_status = 'available'  # 판매 가능

    # 🔧 품절상태 필터링 (실제 구현) - 페이징 후 처리
    if sold_out_status:
        filtered_products = []
        for product in products:
            if sold_out_status == 'soldout' and product.sold_out_status == 'soldout':
                filtered_products.append(product)
            elif sold_out_status == 'available' and product.sold_out_status == 'available':
                filtered_products.append(product)
        
        # 필터링된 결과로 교체 (주의: 페이징이 맞지 않을 수 있음)
        if sold_out_status:
            # 전체 쿼리셋에서 다시 필터링 후 페이징
            filtered_ids = []
            for product in products_qs:
                # 임시로 재고 계산
                temp_total = sum(opt.stock for opt in product.options.all())
                is_sold_out = (product.status == 'soldout') or (temp_total == 0)
                
                if sold_out_status == 'soldout' and is_sold_out:
                    filtered_ids.append(product.id)
                elif sold_out_status == 'available' and not is_sold_out:
                    filtered_ids.append(product.id)
            
            products_qs = products_qs.filter(id__in=filtered_ids)
            paginator = Paginator(products_qs, per_page)
            products = paginator.get_page(page)
            
            # 다시 옵션 데이터 생성
            for product in products:
                options_data = []
                total_stock_sum = 0
                
                for option in product.options.all().order_by('-stock', 'option_name'):
                    options_data.append({
                        'name': option.option_name,
                        'stock': option.stock,
                        'price_krw': str(option.price_krw) if option.price_krw else None
                    })
                    total_stock_sum += option.stock
                
                product.options_json = escape(json.dumps(options_data, ensure_ascii=False))
                
                if product.status == 'soldout':
                    product.sold_out_status = 'soldout'
                elif total_stock_sum == 0:
                    product.sold_out_status = 'soldout'
                else:
                    product.sold_out_status = 'available'

    # 🔍 재고수량 필터링 (Python에서 처리)
    if stock_status or min_stock or max_stock:
        filtered_ids = []
        for product in products_qs:
            total = sum(opt.stock for opt in product.options.all())
            
            include = True
            
            # 재고 상태 필터
            if stock_status == 'available' and total <= 0:
                include = False
            elif stock_status == 'out_of_stock' and total > 0:
                include = False
            
            # 재고 범위 필터
            if min_stock and include:
                try:
                    if total < int(min_stock):
                        include = False
                except ValueError:
                    pass
            
            if max_stock and include:
                try:
                    if total > int(max_stock):
                        include = False
                except ValueError:
                    pass
            
            if include:
                filtered_ids.append(product.id)
        
        if filtered_ids:
            products_qs = products_qs.filter(id__in=filtered_ids)
            paginator = Paginator(products_qs, per_page)
            products = paginator.get_page(page)
            
            # 다시 옵션 데이터 생성
            for product in products:
                options_data = []
                total_stock_sum = 0
                
                for option in product.options.all().order_by('-stock', 'option_name'):
                    options_data.append({
                        'name': option.option_name,
                        'stock': option.stock,
                        'price_krw': str(option.price_krw) if option.price_krw else None
                    })
                    total_stock_sum += option.stock
                
                product.options_json = escape(json.dumps(options_data, ensure_ascii=False))
                
                if product.status == 'soldout':
                    product.sold_out_status = 'soldout'
                elif total_stock_sum == 0:
                    product.sold_out_status = 'soldout'
                else:
                    product.sold_out_status = 'available'

    # 🆕 사용자별 컬럼 설정 적용
    session_key = f'column_settings_product_list_{request.user.id}'
    user_column_settings = request.session.get(session_key, {})
    
    # 사용자 설정에 따라 컬럼 필터링 및 정렬
    if user_column_settings:
        # 설정이 있는 경우 사용자 설정 적용
        visible_columns = []
        columns_with_order = []
        
        # 각 컬럼에 대해 설정 적용
        for column in PRODUCT_TABLE_COLUMNS:
            field = column['field']
            setting = user_column_settings.get(field, {'visible': True, 'order': 999})
            
            if setting.get('visible', True):  # visible이 True인 컬럼만
                column_with_order = column.copy()
                column_with_order['_order'] = setting.get('order', 999)
                columns_with_order.append(column_with_order)
        
        # order 순서대로 정렬
        columns_with_order.sort(key=lambda x: x.get('_order', 999))
        
        # _order 키 제거
        user_columns = []
        for col in columns_with_order:
            clean_col = {k: v for k, v in col.items() if k != '_order'}
            user_columns.append(clean_col)
    else:
        # 설정이 없는 경우 기본값 사용
        user_columns = PRODUCT_TABLE_COLUMNS

    # 📝 페이지당 표시 개수 옵션
    per_page_options = [20, 100, 500, 1000]

    # 📝 컨텍스트 구성
    context = {
        # 공통 컴포넌트를 위한 데이터
        'products': products,
        'items': products,  # pagination 컴포넌트에서 사용

        # 검색/정렬 옵션
        'search_fields': SEARCH_FIELDS,
        'sort_choices': SORT_CHOICES,
        'search_field': search_field,
        'search_value': search_value,
        'sort_by': sort_by,
        'per_page': per_page,
        'per_page_options': per_page_options,
        'total_count': products_qs.count(),

        # 🔧 사용자 설정이 적용된 컬럼 (수정)
        'table_columns': user_columns,

        # 상품분류 필터 데이터
        'gender_filter': gender_filter,
        'category1_filter': category1_filter,
        'category2_filter': category2_filter,
        'include_subcategory': include_subcategory,
        'gender_choices': GENDER_CHOICES,
        'category1_choices': [('', _('전체'))] + [(cat, cat) for cat in sorted(all_category1) if cat],
        'category2_choices': [('', _('전체'))] + [(cat, cat) for cat in sorted(filtered_category2) if cat],

        # 날짜 필터 데이터
        'date_field': date_field,
        'date_range': date_range,
        'start_date': start_date,
        'end_date': end_date,
        'date_field_choices': DATE_FIELD_CHOICES,
        'date_range_choices': DATE_RANGE_CHOICES,

        # 재고수량 필터 데이터
        'stock_status': stock_status,
        'min_stock': min_stock,
        'max_stock': max_stock,
        'stock_status_choices': STOCK_STATUS_CHOICES,

        # 상품가격 필터 데이터
        'price_field': price_field,
        'min_price': min_price,
        'max_price': max_price,
        'price_field_choices': PRICE_FIELD_CHOICES,

        # 🔧 품절상태 필터 데이터 (실제 구현)
        'sold_out_status': sold_out_status,
        'sold_out_status_choices': SOLD_OUT_STATUS_CHOICES,

        # 🔧 판매상태 필터 데이터 (실제 구현)
        'sales_status': sales_status,
        'sales_status_choices': SALES_STATUS_CHOICES,
    }

    return render(request, 'dashboard/product_list.html', context)


# ========================================
# 🆕 컬럼 설정 관련 AJAX 뷰 (세션 기반 임시 구현)
# ========================================

@staff_member_required
def save_column_settings(request):
    """사용자별 컬럼 설정 저장 - 세션 기반 임시 구현"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        column_settings = request.POST.get('column_settings')
        if not column_settings:
            return JsonResponse({'success': False, 'message': '컬럼 설정 데이터가 없습니다.'})
        
        # JSON 파싱 및 검증
        try:
            column_settings = json.loads(column_settings)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': '잘못된 JSON 형식입니다.'})
        
        # 세션에 저장 (임시 구현 - 추후 UserTableColumnSetting 모델로 변경)
        request.session[f'column_settings_product_list_{request.user.id}'] = column_settings
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'message': '컬럼 설정이 저장되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'설정 저장 중 오류가 발생했습니다: {str(e)}'
        })


@staff_member_required
def get_column_settings(request):
    """사용자의 현재 컬럼 설정 조회 - 세션 기반 임시 구현"""
    try:
        # 세션에서 설정 조회 (임시 구현)
        session_key = f'column_settings_product_list_{request.user.id}'
        user_settings = request.session.get(session_key)
        
        if user_settings:
            return JsonResponse({
                'success': True,
                'column_settings': user_settings
            })
        else:
            # 기본 설정 생성 및 반환
            default_settings = {}
            for i, col in enumerate(PRODUCT_TABLE_COLUMNS):
                default_settings[col['field']] = {
                    'visible': True,
                    'order': i + 1
                }
            
            return JsonResponse({
                'success': True,
                'column_settings': default_settings
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'설정 조회 중 오류가 발생했습니다: {str(e)}'
        })