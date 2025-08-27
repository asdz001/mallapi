# shop_product/views/brand.py
# 🏷️ 브랜드 관리 전용 Views - 캐싱 없는 최종 최적화 버전

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
from dictionary.models import Brand, BrandAlias
from shop.models import Product
import time

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
        'type': 'active_badge',
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
        'type': 'code_text',
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

# 🚀 **핵심 최적화 1**: 페이지별 브랜드만 실시간 계산
def calculate_page_brands_product_count(brands_queryset):
    """
    🔥 페이지별 실시간 계산 (캐싱 없음)
    - 현재 페이지의 브랜드들만 상품수 계산 (최대 25개)
    - 실시간 데이터 보장
    - 별칭 매핑을 메모리에서 처리하여 속도 최적화
    """
    if not brands_queryset:
        return []
    
    start_time = time.time()
    
    try:
        # 🎯 1단계: 현재 페이지 브랜드명 목록 추출
        brand_names = [brand.name for brand in brands_queryset]
        
        # 🎯 2단계: 해당 브랜드들의 별칭 정보를 한 번에 가져오기
        alias_mapping = {}
        aliases_qs = BrandAlias.objects.filter(
            brand__name__in=brand_names
        ).select_related('brand')
        
        for alias in aliases_qs:
            brand_name = alias.brand.name
            if brand_name not in alias_mapping:
                alias_mapping[brand_name] = []
            alias_mapping[brand_name].append(alias.alias)
        
        # 🎯 3단계: 각 브랜드별 상품수 계산 (배치 처리)
        for brand in brands_queryset:
            # 검색할 브랜드명 목록 구성 (표준명 + 별칭들)
            search_names = [brand.name]
            if brand.name in alias_mapping:
                search_names.extend(alias_mapping[brand.name])
            
            # 한 번의 IN 쿼리로 해당 브랜드 상품수 계산
            brand.product_count = Product.objects.filter(
                brand_name__in=search_names
            ).count()
        
        execution_time = time.time() - start_time
        print(f"✅ 페이지별 브랜드 상품수 계산 완료: {len(brands_queryset)}개 브랜드, {execution_time:.3f}초")
        
        return brands_queryset
        
    except Exception as e:
        print(f"🚨 브랜드 상품수 계산 오류: {e}")
        # 오류 발생 시 상품수를 0으로 설정
        for brand in brands_queryset:
            brand.product_count = 0
        return brands_queryset

# 🚀 **핵심 최적화 2**: 집계 쿼리로 전체 브랜드 상품수 (상품수 정렬용)
def get_all_brands_product_count_for_sorting():
    """
    🔥 정렬용 전체 브랜드 상품수 계산
    - 상품수 정렬이 필요할 때만 실행
    - 집계 쿼리 + 메모리 연산으로 최적화
    """
    start_time = time.time()
    
    try:
        # 🎯 1단계: 모든 브랜드명별 상품수를 한 번에 집계
        brand_counts_raw = (
            Product.objects
            .exclude(brand_name__isnull=True)
            .exclude(brand_name__exact='')
            .values('brand_name')
            .annotate(count=Count('id'))
        )
        
        # 🎯 2단계: 별칭 매핑 정보 가져오기
        alias_to_standard = {}
        for alias in BrandAlias.objects.select_related('brand'):
            alias_to_standard[alias.alias] = alias.brand.name
        
        # 🎯 3단계: 표준 브랜드별로 상품수 합계 (메모리 연산)
        standard_brand_counts = {}
        
        for item in brand_counts_raw:
            brand_name = item['brand_name']
            count = item['count']
            
            # 별칭인지 확인하여 표준 브랜드명으로 변환
            standard_name = alias_to_standard.get(brand_name, brand_name)
            
            # 표준 브랜드별로 누적
            standard_brand_counts[standard_name] = standard_brand_counts.get(standard_name, 0) + count
        
        execution_time = time.time() - start_time
        print(f"✅ 전체 브랜드 상품수 집계 완료: {execution_time:.3f}초")
        
        return standard_brand_counts
        
    except Exception as e:
        print(f"🚨 전체 브랜드 상품수 계산 오류: {e}")
        return {}

# 🔹 브랜드 목록 페이지 - 최종 최적화 버전
@staff_member_required
def brand_list(request):
    """브랜드 관리 메인 페이지 - 실시간 데이터 보장 + 최적화"""
    
    # 📝 검색 파라미터
    search_field = request.GET.get('search_field', 'name')
    search_value = request.GET.get('search_value', '').strip()
    sort_by = request.GET.get('sort', '-id')
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
            alias_brand_ids = BrandAlias.objects.filter(
                alias__icontains=search_value
            ).values_list('brand_id', flat=True)
            brands_queryset = brands_queryset.filter(id__in=alias_brand_ids)
    
    # 📊 상품수 정렬 여부 확인
    is_product_count_sort = 'product_count' in sort_by
    
    if is_product_count_sort:
        # 🚀 상품수 정렬이 필요한 경우: 전체 브랜드 상품수 계산
        print("🔄 상품수 정렬 모드: 전체 브랜드 상품수 계산 중...")
        
        all_brand_counts = get_all_brands_product_count_for_sorting()
        
        # 각 브랜드에 상품수 정보 추가
        for brand in brands_queryset:
            brand.product_count = all_brand_counts.get(brand.name, 0)
        
        # 상품수로 정렬
        if sort_by == 'product_count':
            brands_queryset = sorted(brands_queryset, key=lambda x: x.product_count)
        elif sort_by == '-product_count':
            brands_queryset = sorted(brands_queryset, key=lambda x: x.product_count, reverse=True)
        
        # 페이지네이션 적용
        paginator = Paginator(brands_queryset, per_page)
        brands = paginator.get_page(page)
        
    else:
        # 🚀 일반 정렬인 경우: 페이지별 최적화
        print("🔄 일반 정렬 모드: 페이지별 브랜드 상품수 계산")
        
        # 일반 정렬 적용
        valid_sort_fields = [choice[0] for choice in SORT_CHOICES if 'product_count' not in choice[0]]
        if sort_by in valid_sort_fields:
            brands_queryset = brands_queryset.order_by(sort_by)
        else:
            brands_queryset = brands_queryset.order_by('-id')
        
        # 페이지네이션 먼저 적용
        paginator = Paginator(brands_queryset, per_page)
        brands = paginator.get_page(page)
        
        # 현재 페이지의 브랜드들만 상품수 계산 (실시간)
        brands.object_list = calculate_page_brands_product_count(brands.object_list)
    
    # 🔗 최근 별칭 목록 (최근 10개)
    recent_aliases = BrandAlias.objects.select_related('brand').order_by('-id')[:10]
    
    # 📊 통계 정보
    total_brands = Brand.objects.count()
    total_aliases = BrandAlias.objects.count()
    active_brands = Brand.objects.filter(is_active=True).count()
    
    # 📋 컨텍스트 구성
    context = {
        'brands': brands,
        'items': brands,
        'recent_aliases': recent_aliases,
        'brand_table_columns': BRAND_TABLE_COLUMNS,
        'alias_table_columns': ALIAS_TABLE_COLUMNS,
        'search_fields': SEARCH_FIELDS,
        'sort_choices': SORT_CHOICES,
        'search_field': search_field,
        'search_value': search_value,
        'sort_by': sort_by,
        'per_page': per_page,
        'per_page_options': [10, 25, 50, 100],
        'total_count': paginator.count,
        'total_brands': total_brands,
        'total_aliases': total_aliases,
        'active_brands': active_brands,
    }
    
    return render(request, 'dashboard/classification/classification_brand.html', context)

# 🔹 개별 브랜드 상품수 계산 (상세보기/수정용)
def calculate_single_brand_product_count(brand_name):
    """개별 브랜드의 실시간 상품수 계산"""
    try:
        # 해당 브랜드의 별칭들 가져오기
        aliases = list(BrandAlias.objects.filter(
            brand__name=brand_name
        ).values_list('alias', flat=True))
        
        # 검색할 브랜드명 목록 (표준명 + 별칭들)
        search_names = [brand_name] + aliases
        
        # IN 쿼리로 한 번에 계산
        return Product.objects.filter(brand_name__in=search_names).count()
        
    except Exception as e:
        print(f"🚨 개별 브랜드 상품수 계산 오류: {e}")
        return 0

# 🔹 표준 브랜드 생성 (AJAX)
@staff_member_required
def brand_create(request):
    """표준 브랜드 생성 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        name = request.POST.get('name', '').strip()
        aliases = request.POST.getlist('aliases[]')
        
        if not name:
            return JsonResponse({'success': False, 'message': '브랜드명은 필수입니다.'})
        
        if Brand.objects.filter(name=name).exists():
            return JsonResponse({'success': False, 'message': f'브랜드 "{name}"은(는) 이미 존재합니다.'})
        
        # 브랜드 생성
        brand = Brand.objects.create(name=name, is_active=True)
        
        # 별칭 생성
        created_aliases = []
        for alias in aliases:
            alias = alias.strip()
            if alias:
                if BrandAlias.objects.filter(alias=alias).exists():
                    brand.delete()  # 롤백
                    return JsonResponse({'success': False, 'message': f'별칭 "{alias}"는 이미 존재합니다.'})
                
                BrandAlias.objects.create(brand=brand, alias=alias)
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
        
        # 실시간 상품수 계산
        product_count = calculate_single_brand_product_count(brand.name)
        
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
    """표준 브랜드 수정 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        brand = get_object_or_404(Brand, id=brand_id)
        name = request.POST.get('name', '').strip()
        aliases = request.POST.getlist('aliases[]')
        
        if not name:
            return JsonResponse({'success': False, 'message': '브랜드명은 필수입니다.'})
        
        if Brand.objects.filter(name=name).exclude(id=brand_id).exists():
            return JsonResponse({'success': False, 'message': f'브랜드 "{name}"은(는) 이미 존재합니다.'})
        
        old_name = brand.name
        brand.name = name
        brand.save()
        
        # 기존 별칭 삭제 후 새로 생성
        BrandAlias.objects.filter(brand=brand).delete()
        
        updated_aliases = []
        for alias in aliases:
            alias = alias.strip()
            if alias:
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
        
        # 실시간 관련 상품 확인
        product_count = calculate_single_brand_product_count(brand_name)
        if product_count > 0:
            return JsonResponse({
                'success': False, 
                'message': f'이 브랜드와 연결된 상품이 {product_count}개 있어 삭제할 수 없습니다.'
            })
        
        # 별칭 확인
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
        alias = request.POST.get('alias', '').strip()
        standard_brand_id = request.POST.get('standard_brand_id')
        
        if not alias:
            return JsonResponse({'success': False, 'message': '치환 브랜드명은 필수입니다.'})
        
        if not standard_brand_id:
            return JsonResponse({'success': False, 'message': '표준 브랜드를 선택해주세요.'})
        
        if BrandAlias.objects.filter(alias=alias).exists():
            return JsonResponse({'success': False, 'message': f'별칭 "{alias}"은(는) 이미 존재합니다.'})
        
        standard_brand = get_object_or_404(Brand, id=standard_brand_id)
        
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

# 🔹 브랜드 활성화/비활성화 토글 (AJAX)
@staff_member_required
def brand_toggle_active(request, brand_id):
    """브랜드 활성화/비활성화 토글 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        brand = get_object_or_404(Brand, id=brand_id)
        
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
        brands = Brand.objects.filter(is_active=True).order_by('name')
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