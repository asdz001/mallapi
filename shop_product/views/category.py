# shop_product/views/category.py

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from dictionary.models import (  # 소문자로 수정
    CategoryLevel1, CategoryLevel1Alias,
    CategoryLevel2, CategoryLevel2Alias, 
    CategoryLevel3, CategoryLevel3Alias,
    CategoryLevel4, CategoryLevel4Alias
)
from shop.models import Product  # Product 모델 임포트 추가
import json

# 🔧 카테고리 레벨별 설정
CATEGORY_LEVELS = {
    'level1': {
        'model': CategoryLevel1,
        'alias_model': CategoryLevel1Alias,
        'name': '성별',
        'field_name': 'name',
        'parent_field': None,
    },
    'level2': {
        'model': CategoryLevel2,
        'alias_model': CategoryLevel2Alias,
        'name': '대분류',
        'field_name': 'name',
        'parent_field': None,  # 현재 모델에 상위관계 없음
    },
    'level3': {
        'model': CategoryLevel3,
        'alias_model': CategoryLevel3Alias,
        'name': '중분류',
        'field_name': 'name',
        'parent_field': None,
    },
    'level4': {
        'model': CategoryLevel4,
        'alias_model': CategoryLevel4Alias,
        'name': '소분류',
        'field_name': 'name',
        'parent_field': None,
    }
}

# 🔧 검색 필드 설정
SEARCH_FIELDS = [
    ('name', '카테고리명'),
    ('alias', 'Alias명'),
]

# 🔧 정렬 옵션
SORT_CHOICES = [
    ('name', '이름 순'),
    ('-name', '이름 역순'),
    ('id', '번호 순'),
    ('-id', '번호 역순'),
    ('product_count', '연결 상품수 순'),
    ('-product_count', '연결 상품수 역순'),
]

# 🔧 테이블 컬럼 설정 (동적으로 생성)
def get_table_columns(level):
    """레벨별 테이블 컬럼 설정을 반환"""
    base_columns = [
        {
            'field': 'id',
            'header': '번호',
            'width': '60px',
            'align': 'center',
            'default': '-'
        },
        {
            'field': 'name',
            'header': CATEGORY_LEVELS[level]['name'],
            'width': '100px',
            'align': 'center',
            'default': '-'
        },
        {
            'field': 'alias_count',
            'header': 'Alias 수',
            'width': '100px',
            'align': 'center',
            'default': '0개'
        },
        {
            'field': 'product_count',
            'header': '연결 상품수',
            'width': '120px',
            'align': 'center',
            'default': '0개'
        }
    ]
    return base_columns

# 🔹 메인 카테고리 관리 페이지
@staff_member_required
def category_list(request):
    """
    통합 카테고리 관리 페이지
    - 4개 레벨을 탭으로 구분하여 관리
    - 기본적으로 level1(성별)을 표시
    """
    # 현재 활성 레벨 가져오기 (기본값: level1)
    current_level = request.GET.get('level', 'level1')
    
    # 유효한 레벨인지 확인
    if current_level not in CATEGORY_LEVELS:
        current_level = 'level1'
    
    # 해당 레벨의 데이터 조회
    level_data = get_level_data(request, current_level)
    
    # 컨텍스트 구성
    context = {
        'current_level': current_level,
        'level_name': CATEGORY_LEVELS[current_level]['name'],
        'categories': level_data['categories'],
        'table_columns': get_table_columns(current_level),
        'search_fields': SEARCH_FIELDS,
        'sort_choices': SORT_CHOICES,
        'search_field': level_data['search_field'],
        'search_value': level_data['search_value'],
        'sort_by': level_data['sort_by'],
        'per_page': level_data['per_page'],
        'per_page_options': [10, 25, 50, 100],
        'total_count': level_data['total_count'],
        'level_tabs': [
            {'key': 'level1', 'name': '성별', 'icon': 'fas fa-venus-mars'},
            {'key': 'level2', 'name': '대분류', 'icon': 'fas fa-layer-group'},
            {'key': 'level3', 'name': '중분류', 'icon': 'fas fa-list'},
            {'key': 'level4', 'name': '소분류', 'icon': 'fas fa-tags'},
        ]
    }
    
    return render(request, 'dashboard/classification/classification_category.html', context)

def get_level_data(request, level):
    """특정 레벨의 카테고리 데이터를 조회하고 페이징 처리"""
    
    # 모델 정보 가져오기
    model = CATEGORY_LEVELS[level]['model']
    alias_model = CATEGORY_LEVELS[level]['alias_model']
    
    # 검색 파라미터
    search_field = request.GET.get('search_field', 'name')
    search_value = request.GET.get('search_value', '').strip()
    sort_by = request.GET.get('sort', 'name')
    per_page = int(request.GET.get('per_page', 25))
    page = request.GET.get('page', 1)
    
    # 기본 쿼리셋 (Alias 수 포함)
    queryset = model.objects.annotate(
        alias_count=Count('aliases')
    )
    
    # 검색 적용
    if search_value:
        if search_field == 'name':
            queryset = queryset.filter(name__icontains=search_value)
        elif search_field == 'alias':
            # Alias 테이블에서 검색
            alias_ids = alias_model.objects.filter(
                alias__icontains=search_value
            ).values_list('category_id', flat=True)
            queryset = queryset.filter(id__in=alias_ids)
    
    # 정렬 적용
    valid_sort_fields = [choice[0] for choice in SORT_CHOICES]
    if sort_by in valid_sort_fields:
        queryset = queryset.order_by(sort_by)
    else:
        queryset = queryset.order_by('name')
    
    # 🔧 각 카테고리에 상품 수 계산 (실제 Product 모델 기반)
    for category in queryset:
        product_count = calculate_product_count(level, category.name)
        category.product_count = product_count
    
    # 페이징 처리
    paginator = Paginator(queryset, per_page)
    categories = paginator.get_page(page)
    
    return {
        'categories': categories,
        'search_field': search_field,
        'search_value': search_value,
        'sort_by': sort_by,
        'per_page': per_page,
        'total_count': queryset.count(),
    }

def calculate_product_count(level, category_name):
    """카테고리별 상품 수 계산 (Alias 포함)"""
    try:
        total_count = 0
        
        if level == 'level1':  # 성별
            # 직접 매치
            count = Product.objects.filter(gender=category_name).count()
            total_count += count
            
            # Alias로 매치 (예: "남성" 카테고리에 "MEN", "MALE" alias가 있을 때)
            aliases = CategoryLevel1Alias.objects.filter(
                category__name=category_name
            ).values_list('alias', flat=True)
            
            for alias in aliases:
                alias_count = Product.objects.filter(gender=alias).count()
                total_count += alias_count
                
        elif level == 'level2':  # 대분류 (category1)
            # 직접 매치
            count = Product.objects.filter(category1=category_name).count()
            total_count += count
            
            # Alias로 매치
            aliases = CategoryLevel2Alias.objects.filter(
                category__name=category_name
            ).values_list('alias', flat=True)
            
            for alias in aliases:
                alias_count = Product.objects.filter(category1=alias).count()
                total_count += alias_count
                
        elif level == 'level3':  # 중분류 (category2)
            # 직접 매치
            count = Product.objects.filter(category2=category_name).count()
            total_count += count
            
            # Alias로 매치
            aliases = CategoryLevel3Alias.objects.filter(
                category__name=category_name
            ).values_list('alias', flat=True)
            
            for alias in aliases:
                alias_count = Product.objects.filter(category2=alias).count()
                total_count += alias_count
                
        elif level == 'level4':  # 소분류 (아직 Product에 해당 필드 없음)
            total_count = 0  # TODO: category3 필드 추가 후 구현
        else:
            total_count = 0
        
        print(f"🔢 DEBUG: {level} '{category_name}' 총 상품 수 = {total_count}")  # 디버깅용
        return total_count
        
    except Exception as e:
        print(f"💥 DEBUG: 상품 수 계산 오류 - {str(e)}")  # 디버깅용
        return 0

# 🔹 카테고리 생성 (AJAX)
@staff_member_required
def category_create(request):
    """카테고리 생성 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        level = request.POST.get('level')
        name = request.POST.get('name', '').strip()
        aliases = request.POST.getlist('aliases[]')  # Alias 배열
        
        # 레벨 유효성 검사
        if level not in CATEGORY_LEVELS:
            return JsonResponse({'success': False, 'message': '잘못된 카테고리 레벨입니다.'})
        
        # 필수 필드 검증
        if not name:
            return JsonResponse({'success': False, 'message': '카테고리명은 필수입니다.'})
        
        # 모델 정보 가져오기
        model = CATEGORY_LEVELS[level]['model']
        alias_model = CATEGORY_LEVELS[level]['alias_model']
        
        # 중복 검사
        if model.objects.filter(name=name).exists():
            return JsonResponse({'success': False, 'message': f'"{name}"은 이미 존재합니다.'})
        
        # 카테고리 생성
        category = model.objects.create(name=name)
        
        # Alias 생성
        for alias in aliases:
            alias = alias.strip()
            if alias and not alias_model.objects.filter(alias=alias).exists():
                alias_model.objects.create(
                    category=category,
                    alias=alias
                )
        
        return JsonResponse({
            'success': True,
            'message': f'{CATEGORY_LEVELS[level]["name"]} "{name}"이(가) 성공적으로 등록되었습니다.',
            'data': {
                'id': category.id,
                'name': category.name,
                'level': level
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'등록 중 오류가 발생했습니다: {str(e)}'})

# 🔹 카테고리 상세 조회 (AJAX)
@staff_member_required
def category_detail(request, level, category_id):
    """카테고리 상세 정보 조회 - AJAX 처리"""
    print(f"🔍 DEBUG: category_detail 호출됨 - level: {level}, category_id: {category_id}")  # 디버깅용
    
    try:
        # 레벨 유효성 검사
        if level not in CATEGORY_LEVELS:
            print(f"❌ DEBUG: 잘못된 레벨 - {level}")  # 디버깅용
            return JsonResponse({'success': False, 'message': '잘못된 카테고리 레벨입니다.'})
        
        model = CATEGORY_LEVELS[level]['model']
        alias_model = CATEGORY_LEVELS[level]['alias_model']
        
        print(f"📋 DEBUG: 모델 정보 - model: {model}, alias_model: {alias_model}")  # 디버깅용
        
        # 카테고리 조회
        category = get_object_or_404(model, id=category_id)
        print(f"✅ DEBUG: 카테고리 조회 성공 - {category.name}")  # 디버깅용
        
        # Alias 목록 조회
        aliases = list(alias_model.objects.filter(category=category).values('id', 'alias'))
        print(f"🏷 DEBUG: Alias 개수 - {len(aliases)}개")  # 디버깅용
        
        return JsonResponse({
            'success': True,
            'data': {
                'id': category.id,
                'name': category.name,
                'level': level,
                'level_name': CATEGORY_LEVELS[level]['name'],
                'aliases': aliases,
                'product_count': 0,  # TODO: 실제 상품 수 계산
            }
        })
        
    except Exception as e:
        print(f"💥 DEBUG: 오류 발생 - {str(e)}")  # 디버깅용
        return JsonResponse({'success': False, 'message': f'조회 중 오류가 발생했습니다: {str(e)}'})

# 🔹 카테고리 수정 (AJAX)
@staff_member_required
def category_update(request, level, category_id):
    """카테고리 수정 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        # 레벨 유효성 검사
        if level not in CATEGORY_LEVELS:
            return JsonResponse({'success': False, 'message': '잘못된 카테고리 레벨입니다.'})
        
        model = CATEGORY_LEVELS[level]['model']
        alias_model = CATEGORY_LEVELS[level]['alias_model']
        
        # 카테고리 조회
        category = get_object_or_404(model, id=category_id)
        
        # 필수 필드 검증
        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'message': '카테고리명은 필수입니다.'})
        
        # 중복 검사 (자기 자신 제외)
        if model.objects.filter(name=name).exclude(id=category_id).exists():
            return JsonResponse({'success': False, 'message': f'"{name}"은 이미 존재합니다.'})
        
        # 카테고리 수정
        category.name = name
        category.save()
        
        # Alias 업데이트 (기존 삭제 후 재생성)
        aliases = request.POST.getlist('aliases[]')
        alias_model.objects.filter(category=category).delete()
        
        for alias in aliases:
            alias = alias.strip()
            if alias and not alias_model.objects.filter(alias=alias).exists():
                alias_model.objects.create(
                    category=category,
                    alias=alias
                )
        
        return JsonResponse({
            'success': True,
            'message': f'{CATEGORY_LEVELS[level]["name"]} "{name}"이(가) 성공적으로 수정되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'수정 중 오류가 발생했습니다: {str(e)}'})

# 🔹 카테고리 삭제 (AJAX)
@staff_member_required
def category_delete(request, level, category_id):
    """카테고리 삭제 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        # 레벨 유효성 검사
        if level not in CATEGORY_LEVELS:
            return JsonResponse({'success': False, 'message': '잘못된 카테고리 레벨입니다.'})
        
        model = CATEGORY_LEVELS[level]['model']
        category = get_object_or_404(model, id=category_id)
        category_name = category.name
        
        # TODO: 관련 상품이 있는지 확인 (필요시)
        # if category.products.exists():
        #     return JsonResponse({'success': False, 'message': '연결된 상품이 있어 삭제할 수 없습니다.'})
        
        # 카테고리 삭제 (Alias는 CASCADE로 자동 삭제)
        category.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'{CATEGORY_LEVELS[level]["name"]} "{category_name}"이(가) 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'삭제 중 오류가 발생했습니다: {str(e)}'})

# 🔹 빠른 등록 (계층구조 한번에 등록)
@staff_member_required
def category_quick_create(request):
    """빠른 카테고리 등록 - 여러 레벨 한번에 등록 (Alias 포함)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        # 각 레벨별 데이터 받기
        level1_name = request.POST.get('level1_name', '').strip()
        level2_name = request.POST.get('level2_name', '').strip()
        level3_name = request.POST.get('level3_name', '').strip()
        level4_name = request.POST.get('level4_name', '').strip()
        
        # 각 레벨별 Alias 데이터 받기
        level1_aliases = request.POST.get('level1_aliases', '').strip()
        level2_aliases = request.POST.get('level2_aliases', '').strip()
        level3_aliases = request.POST.get('level3_aliases', '').strip()
        level4_aliases = request.POST.get('level4_aliases', '').strip()
        
        created_items = []
        
        # Level 1 (성별) 처리
        if level1_name:
            level1, created = CategoryLevel1.objects.get_or_create(name=level1_name)
            if created:
                created_items.append(f'성별: {level1_name}')
                
                # Level 1 Alias 처리
                if level1_aliases:
                    aliases = [alias.strip() for alias in level1_aliases.split(',') if alias.strip()]
                    for alias in aliases:
                        if not CategoryLevel1Alias.objects.filter(alias=alias).exists():
                            CategoryLevel1Alias.objects.create(category=level1, alias=alias)
        
        # Level 2 (대분류) 처리
        if level2_name:
            level2, created = CategoryLevel2.objects.get_or_create(name=level2_name)
            if created:
                created_items.append(f'대분류: {level2_name}')
                
                # Level 2 Alias 처리
                if level2_aliases:
                    aliases = [alias.strip() for alias in level2_aliases.split(',') if alias.strip()]
                    for alias in aliases:
                        if not CategoryLevel2Alias.objects.filter(alias=alias).exists():
                            CategoryLevel2Alias.objects.create(category=level2, alias=alias)
        
        # Level 3 (중분류) 처리
        if level3_name:
            level3, created = CategoryLevel3.objects.get_or_create(name=level3_name)
            if created:
                created_items.append(f'중분류: {level3_name}')
                
                # Level 3 Alias 처리
                if level3_aliases:
                    aliases = [alias.strip() for alias in level3_aliases.split(',') if alias.strip()]
                    for alias in aliases:
                        if not CategoryLevel3Alias.objects.filter(alias=alias).exists():
                            CategoryLevel3Alias.objects.create(category=level3, alias=alias)
        
        # Level 4 (소분류) 처리
        if level4_name:
            level4, created = CategoryLevel4.objects.get_or_create(name=level4_name)
            if created:
                created_items.append(f'소분류: {level4_name}')
                
                # Level 4 Alias 처리
                if level4_aliases:
                    aliases = [alias.strip() for alias in level4_aliases.split(',') if alias.strip()]
                    for alias in aliases:
                        if not CategoryLevel4Alias.objects.filter(alias=alias).exists():
                            CategoryLevel4Alias.objects.create(category=level4, alias=alias)
        
        if created_items:
            message = f'다음 카테고리가 등록되었습니다: {", ".join(created_items)}'
        else:
            message = '모든 카테고리가 이미 존재합니다.'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'created_count': len(created_items)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'등록 중 오류가 발생했습니다: {str(e)}'})

# 🔹 카테고리 옵션 조회 (드롭다운용)
@staff_member_required
def category_options(request, level):
    """특정 레벨의 카테고리 옵션 조회 - 드롭다운용"""
    try:
        if level not in CATEGORY_LEVELS:
            return JsonResponse({'success': False, 'message': '잘못된 레벨입니다.'})
        
        model = CATEGORY_LEVELS[level]['model']
        categories = model.objects.all().order_by('name').values('id', 'name')
        
        return JsonResponse({
            'success': True,
            'options': list(categories)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})