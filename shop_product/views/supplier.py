# shop_product/views/supplier.py 수정 버전
# 🏢 거래처 관리 전용 Views (상품수 계산 기능 추가)

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Case, When
from pricing.models import Retailer
from shop.models import Product  # 상품 수 계산용

# 🔧 테이블 컬럼 설정 (상품수 컬럼 추가)
SUPPLIER_TABLE_COLUMNS = [
    {
        'field': 'id',
        'header': '번호',
        'width': '50px',
        'align': 'center',
        'type': 'text',
        'default': '-'
    },
    {
        'field': 'name',
        'header': '업체명',
        'width': '80px',
        'align': 'center',
        'type': 'text',
        'default': '-'
    },
    {
        'field': 'code',
        'header': '업체코드',
        'width': '50px',
        'align': 'center',
        'type': 'badge',
        'default': '-'
    },
    {
        'field': 'address',
        'header': '주소',
        'width': '150px',
        'align': 'center',
        'type': 'text',
        'truncate': 30,
        'default': '미입력'
    },
    {
        'field': 'phone',
        'header': '연락처',
        'width': '120px',
        'align': 'center',
        'type': 'text',
        'default': '미입력'
    },
    {
        'field': 'product_count',  # 🆕 상품수 컬럼 추가
        'header': '연결 상품수',
        'width': '50px',
        'align': 'center',
        'type': 'count_badge',
        'default': '0'
    },
]

# 🔧 검색 필드 설정
SEARCH_FIELDS = [
    ('name', '업체명'),
    ('code', '업체코드'),
    ('address', '주소'),
    ('phone', '연락처'),
]

# 🔧 정렬 옵션 (상품수 정렬 추가)
SORT_CHOICES = [
    ('name', '업체명 순'),
    ('-name', '업체명 역순'),
    ('code', '업체코드 순'),
    ('-code', '업체코드 역순'),
    ('product_count', '상품수 순'),  # 🆕 추가
    ('-product_count', '상품수 역순'),  # 🆕 추가
    ('id', 'ID 순'),
    ('-id', 'ID 역순'),
]

def calculate_supplier_product_count(retailer_code, retailer_name):
    """거래처별 상품 수 계산 (코드와 이름 모두 확인)"""
    try:
        total_count = 0
        
        # 1. retailer 필드에서 코드로 매치
        code_count = Product.objects.filter(retailer=retailer_code).count()
        total_count += code_count
        
        # 2. retailer 필드에서 이름으로 매치 (중복 제거)
        name_count = Product.objects.filter(retailer=retailer_name).exclude(retailer=retailer_code).count()
        total_count += name_count
        
        print(f"🔍 거래처 상품수 계산: {retailer_name}({retailer_code}) = 코드매치:{code_count} + 이름매치:{name_count} = 총:{total_count}")
        return total_count
        
    except Exception as e:
        print(f"거래처 상품수 계산 오류: {e}")
        return 0

# 🔹 거래처 목록 페이지 (수정)
@staff_member_required
def supplier_list(request):
    """거래처 관리 메인 페이지"""
    
    # 📝 검색 파라미터
    search_field = request.GET.get('search_field', 'name')
    search_value = request.GET.get('search_value', '').strip()
    sort_by = request.GET.get('sort', '-id')  # 기본값: ID 역순
    per_page = int(request.GET.get('per_page', 25))
    page = request.GET.get('page', 1)
    
    # 📝 거래처 쿼리셋
    queryset = Retailer.objects.all()
    
    # 🔍 검색 적용
    if search_value:
        if search_field == 'name':
            queryset = queryset.filter(name__icontains=search_value)
        elif search_field == 'code':
            queryset = queryset.filter(code__icontains=search_value)
        elif search_field == 'address':
            queryset = queryset.filter(address__icontains=search_value)
        elif search_field == 'phone':
            queryset = queryset.filter(phone__icontains=search_value)
    
    # 📊 각 거래처별 상품 수 계산 (수정)
    suppliers_with_count = []
    for supplier in queryset:
        product_count = calculate_supplier_product_count(supplier.code, supplier.name)
        supplier.product_count = product_count
        suppliers_with_count.append(supplier)
    
    # 상품수 정렬 처리 (product_count 기준)
    if sort_by == 'product_count':
        suppliers_with_count.sort(key=lambda x: x.product_count)
    elif sort_by == '-product_count':
        suppliers_with_count.sort(key=lambda x: x.product_count, reverse=True)
    
    # 정렬된 결과로 queryset 업데이트
    if sort_by in ['product_count', '-product_count']:
        supplier_ids = [supplier.id for supplier in suppliers_with_count]
        queryset = Retailer.objects.filter(id__in=supplier_ids)
        # ID 순서 보존
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(supplier_ids)])
        queryset = queryset.order_by(preserved)
        
        # 상품수 다시 설정
        for supplier in queryset:
            supplier.product_count = next(s.product_count for s in suppliers_with_count if s.id == supplier.id)
    else:
        # 📊 정렬 적용 (기존 방식)
        valid_sort_fields = [choice[0] for choice in SORT_CHOICES if choice[0] not in ['product_count', '-product_count']]
        if sort_by in valid_sort_fields:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-id')  # 기본 정렬: ID 역순
        
        # 상품수 설정
        for supplier in queryset:
            supplier.product_count = next(s.product_count for s in suppliers_with_count if s.id == supplier.id)
    
    # 📄 페이지네이션
    paginator = Paginator(queryset, per_page)
    suppliers = paginator.get_page(page)
    
    # 📋 컨텍스트 구성
    context = {
        'suppliers': suppliers,
        'items': suppliers,  # pagination 컴포넌트에서 사용
        'table_columns': SUPPLIER_TABLE_COLUMNS,
        'search_fields': SEARCH_FIELDS,
        'sort_choices': SORT_CHOICES,
        'search_field': search_field,
        'search_value': search_value,
        'sort_by': sort_by,
        'per_page': per_page,
        'per_page_options': [10, 25, 50, 100],
        'total_count': queryset.count(),
    }
    
    return render(request, 'dashboard/classification/classification_supplier.html', context)

# 🔹 거래처 상세보기 (AJAX) - 수정
@staff_member_required
def supplier_detail(request, supplier_id):
    """거래처 상세보기 - AJAX 처리"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        retailer = get_object_or_404(Retailer, id=supplier_id)
        
        # 상품 수 계산 (수정)
        product_count = calculate_supplier_product_count(retailer.code, retailer.name)
        
        return JsonResponse({
            'success': True,
            'data': {
                'id': retailer.id,
                'name': retailer.name,
                'code': retailer.code,
                'address': retailer.address,
                'phone': retailer.phone,
                'business_number': retailer.business_number,
                'email': retailer.email,
                'product_count': product_count,  # 🆕 상품수 추가
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'조회 중 오류가 발생했습니다: {str(e)}'})

# 🔹 거래처 생성 (AJAX)
@staff_member_required
def supplier_create(request):
    """거래처 생성 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        # 📝 필수 필드 검증
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        
        if not name or not code:
            return JsonResponse({'success': False, 'message': '업체명과 업체코드는 필수입니다.'})
        
        # 📝 코드 중복 검사
        if Retailer.objects.filter(code=code).exists():
            return JsonResponse({'success': False, 'message': f'업체코드 "{code}"는 이미 사용 중입니다.'})
        
        # 📝 선택 필드
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()
        business_number = request.POST.get('business_number', '').strip()
        email = request.POST.get('email', '').strip()
        
        # 🆕 거래처 생성
        retailer = Retailer.objects.create(
            name=name,
            code=code,
            address=address if address else None,
            phone=phone if phone else None,
            business_number=business_number if business_number else None,
            email=email if email else None,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'거래처 "{name}"이(가) 성공적으로 등록되었습니다.',
            'data': {
                'id': retailer.id,
                'name': retailer.name,
                'code': retailer.code,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'등록 중 오류가 발생했습니다: {str(e)}'})

# 🔹 거래처 수정 (AJAX)
@staff_member_required
def supplier_update(request, supplier_id):
    """거래처 수정 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        retailer = get_object_or_404(Retailer, id=supplier_id)
        
        # 📝 필수 필드 검증
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        
        if not name or not code:
            return JsonResponse({'success': False, 'message': '업체명과 업체코드는 필수입니다.'})
        
        # 📝 코드 중복 검사 (자기 자신 제외)
        if Retailer.objects.filter(code=code).exclude(id=supplier_id).exists():
            return JsonResponse({'success': False, 'message': f'업체코드 "{code}"는 이미 사용 중입니다.'})
        
        # 📝 필드 업데이트
        old_name = retailer.name
        retailer.name = name
        retailer.code = code
        retailer.address = request.POST.get('address', '').strip() or None
        retailer.phone = request.POST.get('phone', '').strip() or None
        retailer.business_number = request.POST.get('business_number', '').strip() or None
        retailer.email = request.POST.get('email', '').strip() or None
        retailer.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'거래처 "{old_name}"이(가) "{name}"으로 성공적으로 수정되었습니다.',
            'data': {
                'id': retailer.id,
                'name': retailer.name,
                'code': retailer.code,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'수정 중 오류가 발생했습니다: {str(e)}'})

# 🔹 거래처 삭제 (AJAX)
@staff_member_required
def supplier_delete(request, supplier_id):
    """거래처 삭제 - AJAX 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        retailer = get_object_or_404(Retailer, id=supplier_id)
        retailer_name = retailer.name
        
        # 🗑️ 관련 데이터 확인 (수정)
        product_count = calculate_supplier_product_count(retailer.code, retailer.name)
        if product_count > 0:
            return JsonResponse({
                'success': False, 
                'message': f'이 거래처와 연결된 상품이 {product_count}개 있어 삭제할 수 없습니다.'
            })
        
        retailer.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'거래처 "{retailer_name}"이(가) 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'삭제 중 오류가 발생했습니다: {str(e)}'})

# 🔹 기존 뷰 함수들 (다른 분류관리용)
@staff_member_required
def category_list(request):
    return render(request, 'dashboard/classification/classification_category.html')

@staff_member_required
def origin_list(request):
    return render(request, 'dashboard/classification/classification_origin.html')

@staff_member_required
def brand_list(request):
    return render(request, 'dashboard/classification/classification_brand.html')