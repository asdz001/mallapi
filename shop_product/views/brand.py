# shop_product/views/brand.py
# 🏷️ 브랜드 관리 전용 Views

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Case, When
from dictionary.models import Brand, BrandAlias
from shop.models import Product  # 상품 수 계산용

# 🔧 테이블 컬럼 설정 (표준 브랜드용)
BRAND_TABLE_COLUMNS = [
    {
        'field': 'id',
        'header': '번호',
        'width': '80px',
        'align': 'center',
        'type': 'text',
        'default': '-'
    },
    {
        'field': 'name',
        'header': '표준 브랜드명',
        'width': '200px',
        'align': 'left',
        'type': 'text',
        'default': '-'
    },
    {
        'field': 'is_active',
        'header': '서비스 노출',
        'width': '100px',
        'align': 'center',
        'type': 'active_badge',  # 🆕 활성화 상태 표시
        'default': '-'
    },
    {
        'field': 'alias_count',
        'header': '별칭 개수',
        'width': '100px',
        'align': 'center',
        'type': 'count_badge',
        'default': '0'
    },
    {
        'field': 'product_count',
        'header': '연결 상품수',
        'width': '120px',
        'align': 'center',
        'type': 'count_badge',
        'default': '0'
    },
]

# 🔧 별칭 테이블 컬럼 설정
ALIAS_TABLE_COLUMNS = [
    {
        'field': 'alias',
        'header': '치환 브랜드명',
        'width': '200px',
        'align': 'left',
        'type': 'code_text',  # 커스텀 타입 (code 스타일)
        'default': '-'
    },
    {
        'field': 'brand_name',
        'header': '표준 브랜드',
        'width': '150px',
        'align': 'left',
        'type': 'text',
        'default': '-'
    },
]

# 🔧 검색 필드 설정
SEARCH_FIELDS = [
    ('name', '브랜드명'),
    ('alias', '별칭(치환브랜드명)'),
    ('is_active', '서비스 노출 상태'),
]

# 🔧 정렬 옵션
SORT_CHOICES = [
    ('name', '브랜드명 순'),
    ('-name', '브랜드명 역순'),
    ('alias_count', '별칭개수 순'),
    ('-alias_count', '별칭개수 역순'),
    ('product_count', '상품수 순'),
    ('-product_count', '상품수 역순'),
    ('id', '번호 순'),
    ('-id', '번호 역순'),
    ('is_active', '서비스 노출 상태'),
    ('-is_active', '서비스 노출 상태 역순'),
]

# 🔹 브랜드 목록 페이지
@staff_member_required
def brand_list(request):
    """브랜드 관리 메인 페이지 - 표준 브랜드 + 별칭 목록"""
    
    # 📝 검색 파라미터
    search_field = request.GET.get('search_field', 'name')
    search_value = request.GET.get('search_value', '').strip()
    sort_by = request.GET.get('sort', '-id')  # 기본값: ID 역순
    per_page = int(request.GET.get('per_page', 25))
    page = request.GET.get('page', 1)
    
    # 📝 표준 브랜드 쿼리셋 (별칭 개수 포함)
    brands_queryset = Brand.objects.annotate(
        alias_count=Count('aliases')
    )
    
    # 🔍 검색 적용
    if search_value:
        if search_field == 'name':
            brands_queryset = brands_queryset.filter(name__icontains=search_value)
        elif search_field == 'alias':
            # 별칭에서 검색하여 해당하는 표준 브랜드 ID 목록 가져오기
            alias_brand_ids = BrandAlias.objects.filter(
                alias__icontains=search_value
            ).values_list('brand_id', flat=True)
            brands_queryset = brands_queryset.filter(id__in=alias_brand_ids)
    
    # 📊 정렬 적용
    valid_sort_fields = [choice[0] for choice in SORT_CHOICES]
    if sort_by in valid_sort_fields:
        brands_queryset = brands_queryset.order_by(sort_by)
    else:
        brands_queryset = brands_queryset.order_by('-id')  # 기본 정렬: ID 역순
    
    # 📊 각 브랜드별 상품 수 계산 (추가)
    brands_with_count = []
    for brand in brands_queryset:
        product_count = calculate_brand_product_count(brand.name)
        brand.product_count = product_count
        brands_with_count.append(brand)
    
    # 상품수 정렬 처리 (product_count 기준)
    if sort_by == 'product_count':
        brands_with_count.sort(key=lambda x: x.product_count)
    elif sort_by == '-product_count':
        brands_with_count.sort(key=lambda x: x.product_count, reverse=True)
    
    # 정렬된 결과로 queryset 업데이트
    if sort_by in ['product_count', '-product_count']:
        brand_ids = [brand.id for brand in brands_with_count]
        brands_queryset = Brand.objects.filter(id__in=brand_ids).annotate(alias_count=Count('aliases'))
        # ID 순서 보존
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(brand_ids)])
        brands_queryset = brands_queryset.order_by(preserved)
        
        # 상품수 다시 설정
        for brand in brands_queryset:
            brand.product_count = next(b.product_count for b in brands_with_count if b.id == brand.id)
    
    # 📄 페이지네이션 (표준 브랜드)
    paginator = Paginator(brands_queryset, per_page)
    brands = paginator.get_page(page)
    
    # 🔗 최근 별칭 목록 (최근 10개)
    recent_aliases = BrandAlias.objects.select_related('brand').order_by('-id')[:10]
    
    # 📊 통계 정보
    total_brands = Brand.objects.count()
    total_aliases = BrandAlias.objects.count()
    active_brands = brands_queryset.filter(aliases__isnull=False).distinct().count()  # 별칭이 있는 브랜드
    
    # 📋 컨텍스트 구성
    context = {
        # 페이징된 데이터
        'brands': brands,
        'items': brands,  # pagination 컴포넌트에서 사용
        
        # 기타 데이터
        'recent_aliases': recent_aliases,
        
        # 테이블 구조
        'brand_table_columns': BRAND_TABLE_COLUMNS,
        'alias_table_columns': ALIAS_TABLE_COLUMNS,
        
        # 검색/정렬 옵션
        'search_fields': SEARCH_FIELDS,
        'sort_choices': SORT_CHOICES,
        'search_field': search_field,
        'search_value': search_value,
        'sort_by': sort_by,
        'per_page': per_page,
        'per_page_options': [10, 25, 50, 100],
        'total_count': brands_queryset.count(),
        
        # 통계
        'total_brands': total_brands,
        'total_aliases': total_aliases,
        'active_brands': active_brands,
    }
    
    return render(request, 'dashboard/classification/classification_brand.html', context)

def calculate_brand_product_count(brand_name):
    """브랜드별 상품 수 계산 (직접 매치 + 별칭 매치)"""
    try:
        total_count = 0
        
        # 직접 매치 (brand_name 필드와 일치)
        direct_count = Product.objects.filter(brand_name=brand_name).count()
        total_count += direct_count
        
        # 별칭으로 매치 (BrandAlias를 통해 연결된 브랜드명들)
        brand_aliases = BrandAlias.objects.filter(brand__name=brand_name).values_list('alias', flat=True)
        for alias in brand_aliases:
            alias_count = Product.objects.filter(brand_name=alias).count()
            total_count += alias_count
        
        return total_count
        
    except Exception as e:
        print(f"브랜드 상품수 계산 오류: {e}")
        return 0

# 🔹 표준 브랜드 생성 (AJAX)
@staff_member_required
def brand_create(request):
    """표준 브랜드 생성 - AJAX 처리 (별칭 포함)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        # 📝 필수 필드 검증
        name = request.POST.get('name', '').strip()
        aliases = request.POST.getlist('aliases[]')  # 별칭 배열
        
        if not name:
            return JsonResponse({'success': False, 'message': '브랜드명은 필수입니다.'})
        
        # 📝 중복 검사
        if Brand.objects.filter(name=name).exists():
            return JsonResponse({'success': False, 'message': f'브랜드 "{name}"은(는) 이미 존재합니다.'})
        
        # 🆕 브랜드 생성 (기본값: 활성화)
        brand = Brand.objects.create(name=name, is_active=True)
        
        # 🔗 별칭 생성 (있는 경우)
        created_aliases = []
        for alias in aliases:
            alias = alias.strip()
            if alias:
                # 별칭 중복 검사
                if BrandAlias.objects.filter(alias=alias).exists():
                    brand.delete()  # 롤백
                    return JsonResponse({'success': False, 'message': f'별칭 "{alias}"는 이미 존재합니다.'})
                
                brand_alias = BrandAlias.objects.create(brand=brand, alias=alias)
                created_aliases.append(alias)
        
        return JsonResponse({
            'success': True, 
            'message': f'브랜드 "{name}"이(가) 성공적으로 등록되었습니다.',
            'data': {
                'id': brand.id,
                'name': brand.name,
                'is_active': brand.is_active,
                'alias_count': len(created_aliases),
                'aliases': created_aliases,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'등록 중 오류가 발생했습니다: {str(e)}'})

# 🔹 표준 브랜드 상세보기 (AJAX)
@staff_member_required
def brand_detail(request, brand_id):
    """표준 브랜드 상세보기 - AJAX 처리"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        brand = get_object_or_404(Brand, id=brand_id)
        aliases = BrandAlias.objects.filter(brand=brand)
        
        # 상품 수 계산
        product_count = calculate_brand_product_count(brand.name)
        
        return JsonResponse({
            'success': True,
            'data': {
                'id': brand.id,
                'name': brand.name,
                'is_active': brand.is_active,
                'alias_count': aliases.count(),
                'alias_list': [alias.alias for alias in aliases],
                'product_count': product_count,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'조회 중 오류가 발생했습니다: {str(e)}'})

# 🔹 표준 브랜드 수정 (AJAX)
@staff_member_required
def brand_update(request, brand_id):
    """표준 브랜드 수정 - AJAX 처리 (별칭 포함)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        brand = get_object_or_404(Brand, id=brand_id)
        
        # 📝 필수 필드 검증
        name = request.POST.get('name', '').strip()
        aliases = request.POST.getlist('aliases[]')  # 별칭 배열
        
        if not name:
            return JsonResponse({'success': False, 'message': '브랜드명은 필수입니다.'})
        
        # 📝 중복 검사 (자기 자신 제외)
        if Brand.objects.filter(name=name).exclude(id=brand_id).exists():
            return JsonResponse({'success': False, 'message': f'브랜드 "{name}"은(는) 이미 존재합니다.'})
        
        # 📝 브랜드명 수정
        old_name = brand.name
        brand.name = name
        brand.save()
        
        # 🔗 기존 별칭 삭제 후 새로 생성
        BrandAlias.objects.filter(brand=brand).delete()
        
        updated_aliases = []
        for alias in aliases:
            alias = alias.strip()
            if alias:
                # 별칭 중복 검사 (다른 브랜드의 별칭과)
                if BrandAlias.objects.filter(alias=alias).exists():
                    return JsonResponse({'success': False, 'message': f'별칭 "{alias}"는 이미 다른 브랜드에서 사용중입니다.'})
                
                BrandAlias.objects.create(brand=brand, alias=alias)
                updated_aliases.append(alias)
        
        return JsonResponse({
            'success': True, 
            'message': f'브랜드 "{old_name}"이(가) "{name}"으로 성공적으로 수정되었습니다.',
            'data': {
                'id': brand.id,
                'name': brand.name,
                'is_active': brand.is_active,
                'alias_count': len(updated_aliases),
                'aliases': updated_aliases,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'수정 중 오류가 발생했습니다: {str(e)}'})

# 🔹 표준 브랜드 삭제 (AJAX)
@staff_member_required
def brand_delete(request, brand_id):
    """표준 브랜드 삭제 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        brand = get_object_or_404(Brand, id=brand_id)
        brand_name = brand.name
        
        # 🗑️ 관련 데이터 확인
        product_count = calculate_brand_product_count(brand_name)
        if product_count > 0:
            return JsonResponse({
                'success': False, 
                'message': f'이 브랜드와 연결된 상품이 {product_count}개 있어 삭제할 수 없습니다. 먼저 연결된 상품을 정리해주세요.'
            })
        
        # 별칭 개수 확인
        alias_count = BrandAlias.objects.filter(brand=brand).count()
        if alias_count > 0:
            return JsonResponse({
                'success': False, 
                'message': f'이 브랜드에 연결된 별칭이 {alias_count}개 있습니다. 먼저 별칭을 삭제해주세요.'
            })
        
        brand.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'표준 브랜드 "{brand_name}"이(가) 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'삭제 중 오류가 발생했습니다: {str(e)}'})

# 🔹 별칭 생성 (AJAX)
@staff_member_required
def alias_create(request):
    """브랜드 별칭 생성 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        # 📝 필수 필드 검증
        alias = request.POST.get('alias', '').strip()
        standard_brand_id = request.POST.get('standard_brand_id')
        
        if not alias:
            return JsonResponse({'success': False, 'message': '치환 브랜드명은 필수입니다.'})
        
        if not standard_brand_id:
            return JsonResponse({'success': False, 'message': '표준 브랜드를 선택해주세요.'})
        
        # 📝 중복 검사
        if BrandAlias.objects.filter(alias=alias).exists():
            return JsonResponse({'success': False, 'message': f'별칭 "{alias}"은(는) 이미 존재합니다.'})
        
        # 📝 표준 브랜드 존재 확인
        standard_brand = get_object_or_404(Brand, id=standard_brand_id)
        
        # 🆕 별칭 생성
        brand_alias = BrandAlias.objects.create(
            alias=alias,
            brand=standard_brand
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'별칭 "{alias}"이(가) 성공적으로 등록되었습니다.',
            'data': {
                'id': brand_alias.id,
                'alias': brand_alias.alias,
                'brand_name': brand_alias.brand.name,
                'brand_id': brand_alias.brand.id,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'등록 중 오류가 발생했습니다: {str(e)}'})

# 🔹 별칭 삭제 (AJAX)
@staff_member_required
def alias_delete(request, alias_id):
    """브랜드 별칭 삭제 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        brand_alias = get_object_or_404(BrandAlias, id=alias_id)
        alias_name = brand_alias.alias
        
        brand_alias.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'별칭 "{alias_name}"이(가) 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'삭제 중 오류가 발생했습니다: {str(e)}'})

# 🔹 브랜드 활성화/비활성화 토글 (AJAX) - 🆕 추가
@staff_member_required
def brand_toggle_active(request, brand_id):
    """브랜드 활성화/비활성화 토글 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        brand = get_object_or_404(Brand, id=brand_id)
        
        # 상태 토글
        brand.is_active = not brand.is_active
        brand.save()
        
        status_text = "활성화" if brand.is_active else "비활성화"
        
        return JsonResponse({
            'success': True, 
            'message': f'브랜드 "{brand.name}"이(가) {status_text}되었습니다.',
            'data': {
                'id': brand.id,
                'name': brand.name,
                'is_active': brand.is_active,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'상태 변경 중 오류가 발생했습니다: {str(e)}'})

# 🔹 브랜드 옵션 조회 (AJAX)
@staff_member_required
def get_brand_options(request):
    """표준 브랜드 목록 조회 - 별칭 생성시 선택용"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        brands = Brand.objects.filter(is_active=True).order_by('name')  # 🆕 활성화된 브랜드만
        brand_list = [
            {
                'id': brand.id,
                'name': brand.name,
            }
            for brand in brands
        ]
        
        return JsonResponse({
            'success': True,
            'brands': brand_list
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'조회 중 오류가 발생했습니다: {str(e)}'})