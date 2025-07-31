#shop_product/views/product_list.py

from django.shortcuts import render
from shop.models import Product
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.translation import gettext_lazy as _  # 다국어 지원을 위한 import
from datetime import datetime, timedelta  # 🆕 날짜 처리를 위한 import
from django.utils import timezone  # 🆕 시간대 처리

# ========================================
# 🔧 검색 엔진 설정 (새로 추가)
# ========================================
# 검색 가능한 필드들을 여기서 관리합니다
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

# 🆕 품절상태 설정 (UI만, 추후 구현)
SOLD_OUT_STATUS_CHOICES = [
    ('', _('전체')),
    ('sold_out', _('품절됨')),
    ('available', _('품절안됨')),
]

# 🆕 품목판매상태 설정 (UI만, 추후 구현)  
SALES_STATUS_CHOICES = [
    ('', _('전체')),
    ('on_sale', _('진열함')),
    ('off_sale', _('진열안함')),
]

# 🆕 나열기준 설정
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
# 🔧 테이블 컬럼 설정 (여기서 테이블 구조를 관리합니다)
# ========================================
# 새로운 컬럼을 추가하거나 순서를 바꾸려면 이 부분만 수정하면 됩니다!

PRODUCT_TABLE_COLUMNS = [
    {
        'field': 'external_product_id',        # 모델의 필드명
        'header': _('상품ID'),                 # 테이블 헤더에 표시될 이름 (다국어 지원)
        'width': '120px',                      # 컬럼 너비
        'truncate': 15,                        # 15자 이상이면 ...으로 자름
        'align': 'center',                     # 텍스트 정렬
        'type': 'text'                         # 데이터 타입
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
        'type': 'image'                        # 이미지 타입으로 지정
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
        'multiline': True,                     # 2줄까지 표시 허용
        'truncate': 50,                        # 50자 이상이면 자름
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
        'field': 'category_combined',          # 커스텀 필드 (category1 + category2 결합)
        'header': _('카테고리'),
        'width': '150px',
        'type': 'custom'                       # 커스텀 처리가 필요한 필드
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
        'field': 'price_org',
        'header': _('COST'),
        'width': '100px',
        'align': 'right',                      # 숫자는 오른쪽 정렬
        'type': 'currency'                     # 통화 형식으로 표시
    },
    {
        'field': 'markup',
        'header': _('마크업'),
        'width': '80px',
        'align': 'right',
        'type': 'decimal',
        'default': '-'                         # 값이 없을 때 표시할 기본값
    },
    {
        'field': 'price_supply',
        'header': _('공급가'),
        'width': '100px',
        'align': 'right',
        'type': 'currency',
        'format': '0'                          # 소수점 없이 표시
    },
    {
        'field': 'price_retail',
        'header': _('소비자가'),
        'width': '100px',
        'align': 'right',
        'type': 'currency'
    },
    {
        'field': 'calculated_price_krw',
        'header': _('원화가'),
        'width': '100px',
        'align': 'right',
        'type': 'currency',
        'default': '-'
    },
    {
        'field': 'total_stock',
        'header': _('재고'),
        'width': '80px',
        'align': 'center',
        'type': 'number'
    },
    {
        'field': 'status',
        'header': _('상태'),
        'width': '100px',
        'align': 'center',
        'type': 'choice'                       # 선택지 필드 (get_status_display 사용)
    },
    {
        'field': 'created_at',
        'header': _('등록일'),
        'width': '100px',
        'align': 'center',
        'type': 'date',
        'format': 'Y-m-d'                      # 날짜 형식 지정
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
# 🔧 뷰 함수들
# ========================================

def product_list(request):
    """
    상품 리스트 페이지
    - 개선된 검색 엔진 (검색분류 + 검색어)
    - 상품분류 필터 (젠더, 카테고리1, 카테고리2)
    - 날짜 범위 필터 (등록일/수정일 기준)
    - 페이징, 정렬 기능 포함
    - 테이블 설정을 템플릿으로 전달하여 동적으로 테이블 생성
    """
    # 📝 기본 검색 파라미터
    search_field = request.GET.get('search_field', 'product_name')
    search_value = request.GET.get('search_value', '')
    page = request.GET.get('page', 1)
    per_page = int(request.GET.get('per_page', 20))

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

    # 🆕 품절상태 필터 파라미터 (UI만, 추후 구현)
    sold_out_status = request.GET.get('sold_out_status', '')

    # 🆕 품목판매상태 필터 파라미터 (UI만, 추후 구현)
    sales_status = request.GET.get('sales_status', '')

    # 🆕 정렬 기준 파라미터
    sort_by = request.GET.get('sort', '-created_at')  # 기본값: 등록일 역순

    # 📝 검색 분류 유효성 검사
    valid_fields = [field[0] for field in SEARCH_FIELDS]
    if search_field not in valid_fields:
        search_field = 'product_name'

    # 📝 날짜 필드 유효성 검사
    valid_date_fields = [field[0] for field in DATE_FIELD_CHOICES]
    if date_field not in valid_date_fields:
        date_field = 'created_at'

    # 📝 가격 필드 유효성 검사
    valid_price_fields = [field[0] for field in PRICE_FIELD_CHOICES]
    if price_field not in valid_price_fields:
        price_field = 'price_org'

    # 📝 정렬 기준 유효성 검사
    valid_sort_options = [choice[0] for choice in SORT_CHOICES]
    if sort_by not in valid_sort_options:
        sort_by = '-created_at'  # 기본값으로 재설정

    # 🔍 기본 쿼리셋 (정렬 적용)
    products_qs = Product.objects.all().order_by(sort_by)
    
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

    # 🆕 상품분류 필터링
    if gender_filter:
        products_qs = products_qs.filter(gender=gender_filter)
    
    if category1_filter:
        if include_subcategory:
            # 하위분류 포함 검색 (LIKE 검색)
            products_qs = products_qs.filter(category1__icontains=category1_filter)
        else:
            # 정확 일치 검색
            products_qs = products_qs.filter(category1=category1_filter)
    
    if category2_filter:
        if include_subcategory:
            products_qs = products_qs.filter(category2__icontains=category2_filter)
        else:
            products_qs = products_qs.filter(category2=category2_filter)

    # 🆕 날짜 범위 필터링
    if date_range:
        today = timezone.now().date()
        
        if date_range == 'today':
            start_date_obj = today
            end_date_obj = today
        elif date_range == 'yesterday':
            start_date_obj = today - timedelta(days=1)
            end_date_obj = today - timedelta(days=1)
        elif date_range == '3days':
            start_date_obj = today - timedelta(days=3)
            end_date_obj = today
        elif date_range == '7days':
            start_date_obj = today - timedelta(days=7)
            end_date_obj = today
        elif date_range == '1month':
            start_date_obj = today - timedelta(days=30)
            end_date_obj = today
        elif date_range == '3months':
            start_date_obj = today - timedelta(days=90)
            end_date_obj = today
        else:
            start_date_obj = None
            end_date_obj = None
            
        # 날짜 범위 적용
        if start_date_obj and end_date_obj:
            if date_field == 'created_at':
                products_qs = products_qs.filter(
                    created_at__date__gte=start_date_obj,
                    created_at__date__lte=end_date_obj
                )
            elif date_field == 'updated_at':
                products_qs = products_qs.filter(
                    updated_at__date__gte=start_date_obj,
                    updated_at__date__lte=end_date_obj
                )
    
    # 직접 입력 날짜 범위 처리
    elif start_date or end_date:
        try:
            if start_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                if date_field == 'created_at':
                    products_qs = products_qs.filter(created_at__date__gte=start_date_obj)
                else:
                    products_qs = products_qs.filter(updated_at__date__gte=start_date_obj)
            
            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                if date_field == 'created_at':
                    products_qs = products_qs.filter(created_at__date__lte=end_date_obj)
                else:
                    products_qs = products_qs.filter(updated_at__date__lte=end_date_obj)
        except ValueError:
            # 잘못된 날짜 형식은 무시
            pass

    # 🆕 재고수량 필터링
    if stock_status:
        if stock_status == 'available':
            # 재고있음 (total_stock > 0)
            products_qs = products_qs.filter(id__in=[
                p.id for p in products_qs if p.total_stock > 0
            ])
        elif stock_status == 'out_of_stock':
            # 재고없음 (total_stock = 0)
            products_qs = products_qs.filter(id__in=[
                p.id for p in products_qs if p.total_stock == 0
            ])
    
    # 재고수량 범위 필터링
    if min_stock or max_stock:
        # total_stock은 프로퍼티라서 DB에서 직접 필터링 어려움
        # 메모리에서 필터링 수행
        filtered_ids = []
        for product in products_qs:
            total = product.total_stock
            include = True
            
            if min_stock:
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
        
        products_qs = products_qs.filter(id__in=filtered_ids)

    # 🆕 상품가격 필터링
    if min_price or max_price:
        price_filter = {}
        
        try:
            if min_price:
                price_filter[f'{price_field}__gte'] = float(min_price)
            if max_price:
                price_filter[f'{price_field}__lte'] = float(max_price)
            
            # calculated_price_krw는 null 값이 있을 수 있으므로 예외 처리
            if price_field == 'calculated_price_krw':
                price_filter[f'{price_field}__isnull'] = False
            
            products_qs = products_qs.filter(**price_filter)
            
        except ValueError:
            # 잘못된 가격 형식은 무시
            pass

    # 🆕 품절상태 필터링 (추후 구현 예정)
    # TODO: 실제 품절상태 필드 추가 후 구현
    # if sold_out_status:
    #     products_qs = products_qs.filter(sold_out_status=sold_out_status)

    # 🆕 품목판매상태 필터링 (추후 구현 예정)  
    # TODO: 실제 판매상태 필드 추가 후 구현
    # if sales_status:
    #     products_qs = products_qs.filter(sales_status=sales_status)

    # 📝 동적 데이터 수집 (드롭다운 옵션용)
    all_category1 = Product.objects.values_list('category1', flat=True).distinct().exclude(category1__isnull=True).exclude(category1__exact='')
    all_category2 = Product.objects.values_list('category2', flat=True).distinct().exclude(category2__isnull=True).exclude(category2__exact='')
    
    # 카테고리1 선택 시 해당하는 카테고리2만 필터링
    if category1_filter:
        filtered_category2 = Product.objects.filter(category1=category1_filter).values_list('category2', flat=True).distinct().exclude(category2__isnull=True).exclude(category2__exact='')
    else:
        filtered_category2 = all_category2

    # 📝 페이징 처리
    paginator = Paginator(products_qs, per_page)
    products = paginator.get_page(page)
    
    # 📝 페이지당 표시 개수 옵션
    per_page_options = [20, 100, 500, 1000]

    # 📝 템플릿으로 전달할 데이터 준비
    context = {
        'products': products,                    # 페이징된 상품 목록
        'search_field': search_field,            # 선택된 검색 분류
        'search_value': search_value,            # 검색어
        'search_fields': SEARCH_FIELDS,          # 검색 분류 옵션들
        'per_page': per_page,                    # 현재 페이지당 표시 개수
        'page': page,                            # 현재 페이지
        'per_page_options': per_page_options,    # 페이지당 표시 개수 선택옵션
        'table_columns': PRODUCT_TABLE_COLUMNS,  # 테이블 컬럼 설정
        
        # 🆕 상품분류 필터 데이터
        'gender_filter': gender_filter,
        'category1_filter': category1_filter,
        'category2_filter': category2_filter,
        'include_subcategory': include_subcategory,
        'gender_choices': GENDER_CHOICES,
        'category1_choices': [('', _('전체'))] + [(cat, cat) for cat in sorted(all_category1) if cat],
        'category2_choices': [('', _('전체'))] + [(cat, cat) for cat in sorted(filtered_category2) if cat],
        
        # 🆕 날짜 필터 데이터
        'date_field': date_field,
        'date_range': date_range,
        'start_date': start_date,
        'end_date': end_date,
        'date_field_choices': DATE_FIELD_CHOICES,
        'date_range_choices': DATE_RANGE_CHOICES,

        # 🆕 재고수량 필터 데이터
        'stock_status': stock_status,
        'min_stock': min_stock,
        'max_stock': max_stock,
        'stock_status_choices': STOCK_STATUS_CHOICES,

        # 🆕 상품가격 필터 데이터
        'price_field': price_field,
        'min_price': min_price,
        'max_price': max_price,
        'price_field_choices': PRICE_FIELD_CHOICES,

        # 🆕 품절상태 필터 데이터 (UI만)
        'sold_out_status': sold_out_status,
        'sold_out_status_choices': SOLD_OUT_STATUS_CHOICES,

        # 🆕 품목판매상태 필터 데이터 (UI만)
        'sales_status': sales_status,
        'sales_status_choices': SALES_STATUS_CHOICES,

        # 🆕 정렬 기준 데이터
        'sort_by': sort_by,
        'sort_choices': SORT_CHOICES,
    }

    return render(request, 'dashboard/product_list.html', context)

