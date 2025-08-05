from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q
from pricing.models import Retailer
import json

# 🔧 테이블 컬럼 설정 (거래처용) - 기존 필드만 사용
SUPPLIER_TABLE_COLUMNS = [
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
        'header': '업체명',
        'width': '100px',
        'align': 'left',
        'type': 'text',
        'default': '-'
    },
    {
        'field': 'code',
        'header': '업체코드',
        'width': '100px',
        'align': 'center',
        'type': 'badge',  # Badge 스타일로 표시
        'default': '-'
    },
    # {
    #    'field': 'order_api_name',
    #    'header': '주문용 리테일러명',
    #    'width': '180px',
    #    'align': 'left',
    #    'type': 'text',
    #    'default': '미설정',
    #    'default': '-'
    # }
]

# 🔧 검색 필드 설정
SEARCH_FIELDS = [
    ('name', '업체명'),
    ('code', '업체코드'),
    ('address', '회사주소'),
    ('phone', '연락처'),
]

# 🔧 정렬 옵션 - 기존 필드만 사용
SORT_CHOICES = [
    ('name', '업체명 순'),
    ('-name', '업체명 역순'),
    ('code', '업체코드 순'),
    ('-code', '업체코드 역순'),
    ('id', 'ID 순'),
    ('-id', 'ID 역순'),
]

# 🔹 거래처 목록 페이지
@staff_member_required
def supplier_list(request):
    """거래처 목록 페이지 - 검색, 페이징, 정렬 기능 포함"""
    
    # 📝 검색 파라미터
    search_field = request.GET.get('search_field', 'name')
    search_value = request.GET.get('search_value', '').strip()
    sort_by = request.GET.get('sort', '-id')  # 기본값: ID 역순
    per_page = int(request.GET.get('per_page', 25))
    page = request.GET.get('page', 1)
    
    # 📝 기본 쿼리셋
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
    
    # 📊 정렬 적용
    valid_sort_fields = [choice[0] for choice in SORT_CHOICES]
    if sort_by in valid_sort_fields:
        queryset = queryset.order_by(sort_by)
    else:
        queryset = queryset.order_by('-id')  # 기본 정렬: ID 역순
    
    # 📄 페이지네이션
    paginator = Paginator(queryset, per_page)
    suppliers = paginator.get_page(page)
    
    # 📋 컨텍스트 구성
    context = {
        'suppliers': suppliers,
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
                'code': retailer.code
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'등록 중 오류가 발생했습니다: {str(e)}'})

# 🔹 거래처 상세 조회 (AJAX)
@staff_member_required
def supplier_detail(request, supplier_id):
    """거래처 상세 정보 조회 - AJAX 처리"""
    try:
        retailer = get_object_or_404(Retailer, id=supplier_id)
        
        return JsonResponse({
            'success': True,
            'data': {
                'id': retailer.id,
                'name': retailer.name,
                'code': retailer.code,
                'address': retailer.address or '',
                'phone': retailer.phone or '',
                'business_number': retailer.business_number or '',
                'email': retailer.email or '',
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'조회 중 오류가 발생했습니다: {str(e)}'})

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
        
        # 📝 선택 필드
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()
        business_number = request.POST.get('business_number', '').strip()
        email = request.POST.get('email', '').strip()
        
        # 🔄 거래처 수정
        retailer.name = name
        retailer.code = code
        retailer.address = address if address else None
        retailer.phone = phone if phone else None
        retailer.business_number = business_number if business_number else None
        retailer.email = email if email else None
        retailer.updated_by = request.user
        retailer.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'거래처 "{name}"이(가) 성공적으로 수정되었습니다.'
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
        
        # 🗑️ 관련 데이터 확인 (필요시 추가)
        # related_products = retailer.products.count()  # 관련 상품이 있는지 확인
        # if related_products > 0:
        #     return JsonResponse({'success': False, 'message': f'이 거래처와 연결된 상품이 {related_products}개 있어 삭제할 수 없습니다.'})
        
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