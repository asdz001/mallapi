# shop_product/views/origin.py
# 🌍 원산지 관리 전용 Views

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count
from pricing.models import FixedCountry, CountryAlias

# 🔧 테이블 컬럼 설정 (표준국가용)
COUNTRY_TABLE_COLUMNS = [
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
        'header': '국가명',
        'width': '150px',
        'align': 'left',
        'type': 'text',
        'default': '-'
    },
    {
        'field': 'fta_applicable',
        'header': 'FTA 적용',
        'width': '100px',
        'align': 'center',
        'type': 'fta_badge',  # 커스텀 타입
        'default': '-'
    },
    {
        'field': 'alias_count',
        'header': '별칭 개수',
        'width': '100px',
        'align': 'center',
        'type': 'count_badge',  # 커스텀 타입
        'default': '0'
    },
]

# 🔧 별칭 테이블 컬럼 설정
ALIAS_TABLE_COLUMNS = [
    {
        'field': 'origin_name',
        'header': '원본 국가명',
        'width': '200px',
        'align': 'left',
        'type': 'code_text',  # 커스텀 타입 (code 스타일)
        'default': '-'
    },
    {
        'field': 'standard_country_name',
        'header': '표준 국가',
        'width': '150px',
        'align': 'left',
        'type': 'text',
        'default': '-'
    },
    {
        'field': 'fta_info',
        'header': 'FTA 정보',
        'width': '100px',
        'align': 'center',
        'type': 'fta_info_badge',  # 커스텀 타입
        'default': '-'
    },
]

# 🔧 검색 필드 설정
SEARCH_FIELDS = [
    ('name', '국가명'),
    ('fta_applicable', 'FTA적용여부'),
    ('origin_name', '별칭(원본국가명)'),  # 🆕 1. origin_name 검색 추가
]

# 🔧 정렬 옵션
SORT_CHOICES = [
    ('name', '국가명 순'),
    ('-name', '국가명 역순'),
    ('fta_applicable', 'FTA적용 순'),
    ('-fta_applicable', 'FTA적용 역순'),
    ('alias_count', '별칭개수 순'),
    ('-alias_count', '별칭개수 역순'),
    ('id', 'ID 순'),
    ('-id', 'ID 역순'),
]

# 🔹 원산지 목록 페이지
@staff_member_required
def origin_list(request):
    """원산지 관리 메인 페이지 - 표준국가 + 별칭 목록"""
    
    # 📝 검색 파라미터
    search_field = request.GET.get('search_field', 'name')
    search_value = request.GET.get('search_value', '').strip()
    sort_by = request.GET.get('sort', '-id')  # 기본값: ID 역순
    per_page = int(request.GET.get('per_page', 25))
    page = request.GET.get('page', 1)
    
    # 📝 표준국가 쿼리셋 (별칭 개수 포함)
    countries_queryset = FixedCountry.objects.annotate(
        alias_count=Count('countryalias')
    )
    
    # 🔍 검색 적용
    if search_value:
        if search_field == 'name':
            countries_queryset = countries_queryset.filter(name__icontains=search_value)
        elif search_field == 'fta_applicable':
            if search_value.lower() in ['적용', 'fta', 'true', '1', 'o', 'yes']:
                countries_queryset = countries_queryset.filter(fta_applicable=True)
            elif search_value.lower() in ['미적용', 'false', '0', 'x', 'no']:
                countries_queryset = countries_queryset.filter(fta_applicable=False)
        elif search_field == 'origin_name':  # 🆕 1. origin_name 검색 구현
            # 별칭에서 검색하여 해당하는 표준국가 ID 목록 가져오기
            alias_country_ids = CountryAlias.objects.filter(
                origin_name__icontains=search_value
            ).values_list('standard_country_id', flat=True)
            countries_queryset = countries_queryset.filter(id__in=alias_country_ids)
    
    # 📊 정렬 적용
    valid_sort_fields = [choice[0] for choice in SORT_CHOICES]
    if sort_by in valid_sort_fields:
        countries_queryset = countries_queryset.order_by(sort_by)
    else:
        countries_queryset = countries_queryset.order_by('-id')  # 기본 정렬: ID 역순
    
    # 📄 페이지네이션 (표준국가)
    paginator = Paginator(countries_queryset, per_page)
    countries = paginator.get_page(page)
    
    # 🔗 최근 별칭 목록 (최근 10개)
    recent_aliases = CountryAlias.objects.select_related('standard_country').order_by('-id')[:10]
    
    # 📊 통계 정보
    total_countries = FixedCountry.objects.count()
    total_aliases = CountryAlias.objects.count()
    fta_countries = FixedCountry.objects.filter(fta_applicable=True).count()
    non_fta_countries = FixedCountry.objects.filter(fta_applicable=False).count()
    
    # 📋 컨텍스트 구성 (🆕 2. pagination_info와 pagination 사용을 위한 구조)
    context = {
        # 🆕 공통 컴포넌트 사용을 위한 데이터 (pagination_info.html에서 items로 사용)
        'countries': countries,  # 페이징된 데이터 (pagination 컴포넌트에서 items로 사용)
        'items': countries,      # pagination_info.html과 pagination.html에서 사용
        
        # 기타 데이터
        'recent_aliases': recent_aliases,
        
        # 테이블 구조
        'country_table_columns': COUNTRY_TABLE_COLUMNS,
        'alias_table_columns': ALIAS_TABLE_COLUMNS,
        
        # 검색/정렬 옵션 (공통 컴포넌트에서 사용)
        'search_fields': SEARCH_FIELDS,
        'sort_choices': SORT_CHOICES,
        'search_field': search_field,
        'search_value': search_value,
        'sort_by': sort_by,
        'per_page': per_page,
        'per_page_options': [10, 25, 50, 100],
        'total_count': countries_queryset.count(),
        
        # 통계
        'total_countries': total_countries,
        'total_aliases': total_aliases,
        'fta_countries': fta_countries,
        'non_fta_countries': non_fta_countries,
    }
    
    return render(request, 'dashboard/classification/classification_origin.html', context)

# 🔹 표준국가 생성 (AJAX)
@staff_member_required
def country_create(request):
    """표준국가 생성 - AJAX 처리 (별칭 포함)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        # 📝 필수 필드 검증
        name = request.POST.get('name', '').strip()
        fta_applicable = request.POST.get('fta_applicable') == 'on'
        aliases = request.POST.getlist('aliases[]')  # 별칭 배열
        
        if not name:
            return JsonResponse({'success': False, 'message': '국가명은 필수입니다.'})
        
        # 📝 중복 검사
        if FixedCountry.objects.filter(name=name).exists():
            return JsonResponse({'success': False, 'message': f'국가 "{name}"은(는) 이미 존재합니다.'})
        
        # 🆕 표준국가 생성
        country = FixedCountry.objects.create(
            name=name,
            fta_applicable=fta_applicable
        )
        
        # 🔗 별칭 생성
        created_aliases = []
        for alias_name in aliases:
            alias_name = alias_name.strip()
            if alias_name and not CountryAlias.objects.filter(origin_name=alias_name).exists():
                alias = CountryAlias.objects.create(
                    origin_name=alias_name,
                    standard_country=country
                )
                created_aliases.append(alias_name)
        
        return JsonResponse({
            'success': True, 
            'message': f'표준국가 "{name}"이(가) 성공적으로 등록되었습니다. (별칭 {len(created_aliases)}개)',
            'data': {
                'id': country.id,
                'name': country.name,
                'fta_applicable': country.fta_applicable,
                'aliases': created_aliases
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'등록 중 오류가 발생했습니다: {str(e)}'})

# 🔹 표준국가 상세 조회 (AJAX)
@staff_member_required
def country_detail(request, country_id):
    """표준국가 상세 정보 조회 - AJAX 처리"""
    try:
        country = get_object_or_404(FixedCountry, id=country_id)
        
        # 연결된 별칭 목록
        aliases = CountryAlias.objects.filter(standard_country=country).order_by('origin_name')
        alias_list = [alias.origin_name for alias in aliases]
        
        return JsonResponse({
            'success': True,
            'data': {
                'id': country.id,
                'name': country.name,
                'fta_applicable': country.fta_applicable,
                'alias_count': aliases.count(),
                'alias_list': alias_list,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'조회 중 오류가 발생했습니다: {str(e)}'})

# 🔹 표준국가 수정 (AJAX)
@staff_member_required
def country_update(request, country_id):
    """표준국가 수정 - AJAX 처리 (별칭 포함)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        country = get_object_or_404(FixedCountry, id=country_id)
        
        # 📝 필드 값 가져오기
        name = request.POST.get('name', '').strip()
        fta_applicable = request.POST.get('fta_applicable') == 'on'
        aliases = request.POST.getlist('aliases[]')  # 별칭 배열
        
        if not name:
            return JsonResponse({'success': False, 'message': '국가명은 필수입니다.'})
        
        # 📝 중복 검사 (자기 자신 제외)
        if FixedCountry.objects.filter(name=name).exclude(id=country_id).exists():
            return JsonResponse({'success': False, 'message': f'국가 "{name}"은(는) 이미 존재합니다.'})
        
        # 💾 수정 저장
        country.name = name
        country.fta_applicable = fta_applicable
        country.save()
        
        # 🔗 기존 별칭 삭제 후 새로 생성
        CountryAlias.objects.filter(standard_country=country).delete()
        
        created_aliases = []
        for alias_name in aliases:
            alias_name = alias_name.strip()
            if alias_name and not CountryAlias.objects.filter(origin_name=alias_name).exists():
                alias = CountryAlias.objects.create(
                    origin_name=alias_name,
                    standard_country=country
                )
                created_aliases.append(alias_name)
        
        return JsonResponse({
            'success': True,
            'message': f'표준국가 "{name}"이(가) 성공적으로 수정되었습니다. (별칭 {len(created_aliases)}개)',
            'data': {
                'id': country.id,
                'name': country.name,
                'fta_applicable': country.fta_applicable,
                'aliases': created_aliases
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'수정 중 오류가 발생했습니다: {str(e)}'})

# 🔹 표준국가 삭제 (AJAX)
@staff_member_required
def country_delete(request, country_id):
    """표준국가 삭제 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        country = get_object_or_404(FixedCountry, id=country_id)
        country_name = country.name
        
        # 🔗 관련 별칭 확인
        alias_count = CountryAlias.objects.filter(standard_country=country).count()
        if alias_count > 0:
            return JsonResponse({
                'success': False, 
                'message': f'이 국가와 연결된 별칭이 {alias_count}개 있어 삭제할 수 없습니다. 먼저 별칭을 삭제해주세요.'
            })
        
        country.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'표준국가 "{country_name}"이(가) 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'삭제 중 오류가 발생했습니다: {str(e)}'})

# 🔹 별칭 생성 (AJAX)
@staff_member_required
def alias_create(request):
    """원산지 별칭 생성 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        # 📝 필수 필드 검증
        origin_name = request.POST.get('origin_name', '').strip()
        standard_country_id = request.POST.get('standard_country_id')
        
        if not origin_name:
            return JsonResponse({'success': False, 'message': '원본 국가명은 필수입니다.'})
        
        if not standard_country_id:
            return JsonResponse({'success': False, 'message': '표준 국가를 선택해주세요.'})
        
        # 📝 중복 검사
        if CountryAlias.objects.filter(origin_name=origin_name).exists():
            return JsonResponse({'success': False, 'message': f'별칭 "{origin_name}"은(는) 이미 존재합니다.'})
        
        # 📝 표준국가 존재 확인
        standard_country = get_object_or_404(FixedCountry, id=standard_country_id)
        
        # 🆕 별칭 생성
        alias = CountryAlias.objects.create(
            origin_name=origin_name,
            standard_country=standard_country
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'별칭 "{origin_name}"이(가) 성공적으로 등록되었습니다.',
            'data': {
                'id': alias.id,
                'origin_name': alias.origin_name,
                'standard_country_name': alias.standard_country.name,
                'standard_country_id': alias.standard_country.id,
                'fta_applicable': alias.standard_country.fta_applicable,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'등록 중 오류가 발생했습니다: {str(e)}'})

# 🔹 별칭 삭제 (AJAX)
@staff_member_required
def alias_delete(request, alias_id):
    """원산지 별칭 삭제 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        alias = get_object_or_404(CountryAlias, id=alias_id)
        origin_name = alias.origin_name
        
        alias.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'별칭 "{origin_name}"이(가) 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'삭제 중 오류가 발생했습니다: {str(e)}'})

# 🔹 표준국가 목록 조회 (AJAX) - 별칭 등록 시 드롭다운용
@staff_member_required
def get_country_options(request):
    """표준국가 목록 조회 - 별칭 등록 드롭다운용"""
    try:
        countries = FixedCountry.objects.all().order_by('name')
        
        country_list = []
        for country in countries:
            country_list.append({
                'id': country.id,
                'name': country.name,
                'fta_applicable': country.fta_applicable,
                'display_name': f"{country.name}" + (" (FTA)" if country.fta_applicable else "")
            })
        
        return JsonResponse({
            'success': True,
            'data': country_list
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'조회 중 오류가 발생했습니다: {str(e)}'})