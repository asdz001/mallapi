from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.timezone import localtime
from django.http import JsonResponse
from members.models import Member
from datetime import datetime, timedelta

# ✅ 테이블 컬럼 정의 (table_filters.py 호환 구조)
COLUMNS = [
    {
        "field": "username",
        "header": "아이디",
        "type": "text",
        "align": "left",
        "width": "120px",
        "truncate": 15
    },
    {
        "field": "name",
        "header": "이름",
        "type": "text",
        "align": "center",
        "width": "100px",
        "default": "미입력"
    },
    {
        "field": "user_type",
        "header": "회원유형",
        "type": "choice",
        "align": "center",
        "width": "90px",
        "default": "일반"
    },
    {
        "field": "email",
        "header": "이메일",
        "type": "text",
        "align": "left",
        "width": "200px",
        "truncate": 25,
        "default": "미입력"
    },
    {
        "field": "mobile",
        "header": "휴대폰",
        "type": "text",
        "align": "center",
        "width": "120px",
        "default": "미입력"
    },
    {
        "field": "gender",
        "header": "성별",
        "type": "choice",
        "align": "center",
        "width": "70px",
        "default": "미입력"
    },
    {
        "field": "birthdate",
        "header": "생년월일",
        "type": "date",
        "align": "center",
        "width": "100px",
        "format": "Y-m-d",
        "default": "미입력"
    },
    {
        "field": "created_at",
        "header": "가입일",
        "type": "date",
        "align": "center",
        "width": "120px",
        "format": "Y-m-d H:i"
    },
    {
        "field": "is_active",
        "header": "상태",
        "type": "choice",
        "align": "center",
        "width": "20px"
    },
]

# ✅ 검색 필드 옵션
SEARCH_FIELDS = [
    ('username', '아이디'),
    ('name', '이름'),
    ('email', '이메일'),
    ('mobile', '휴대폰'),
]

# ✅ 회원유형 선택지 (실제 모델에 맞게 수정 필요)
USER_TYPE_CHOICES = [
    ('', '전체'),
    ('general', '일반회원'),
    ('business', '사업자회원'),
    ('admin', '관리자'),
]

# ✅ 상태 선택지
STATUS_CHOICES = [
    ('', '전체'),
    ('active', '활성'),
    ('inactive', '비활성'),
]

# ✅ 페이지당 표시 옵션
PER_PAGE_OPTIONS = [10, 25, 50, 100]

def member_list(request):
    """
    🎯 회원 목록 뷰 함수
    - 검색/필터링 기능
    - 페이지네이션
    - 정렬 기능
    """
    
    # 📊 기본 쿼리셋
    queryset = Member.objects.all()
    
    # 🔍 검색 파라미터 가져오기
    search_field = request.GET.get('search_field', 'username')
    search_value = request.GET.get('search_value', '').strip()
    user_type = request.GET.get('user_type', '')
    status = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # 🔍 기본 검색 적용
    if search_value:
        if search_field == 'username':
            queryset = queryset.filter(username__icontains=search_value)
        elif search_field == 'name':
            queryset = queryset.filter(name__icontains=search_value)
        elif search_field == 'email':
            queryset = queryset.filter(email__icontains=search_value)
        elif search_field == 'mobile':
            queryset = queryset.filter(mobile__icontains=search_value)
    
    # 🔍 회원유형 필터
    if user_type:
        # 실제 모델 필드명에 맞게 수정 필요
        if hasattr(Member, 'user_type'):
            queryset = queryset.filter(user_type=user_type)
        # 또는 다른 방식으로 회원유형 구분
    
    # 🔍 상태 필터
    if status:
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
    
    # 🔍 가입일 필터
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__gte=start_date_obj)
        except ValueError:
            pass  # 잘못된 날짜 형식은 무시
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__lte=end_date_obj)
        except ValueError:
            pass  # 잘못된 날짜 형식은 무시
    
    # 📊 정렬 적용 (기본: 최신가입순)
    sort_by = request.GET.get('sort', '-created_at')
    valid_sort_fields = [
        'username', '-username',
        'name', '-name', 
        'email', '-email',
        'created_at', '-created_at',
        'is_active', '-is_active'
    ]
    
    if sort_by in valid_sort_fields:
        queryset = queryset.order_by(sort_by)
    else:
        queryset = queryset.order_by('-created_at')  # 기본 정렬
    
    # 📄 페이지네이션 설정
    per_page = int(request.GET.get('per_page', 25))
    if per_page not in PER_PAGE_OPTIONS:
        per_page = 25  # 기본값
    
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)
    
    try:
        members = paginator.get_page(page_number)
    except:
        members = paginator.get_page(1)  # 페이지 오류 시 첫 페이지로
    
    # 📋 컨텍스트 구성
    context = {
        # 테이블 설정
        'columns': COLUMNS,
        'members': members,
        
        # 검색/필터 옵션
        'search_fields': SEARCH_FIELDS,
        'user_type_choices': USER_TYPE_CHOICES,
        'status_choices': STATUS_CHOICES,
        'per_page_options': PER_PAGE_OPTIONS,
        
        # 현재 검색/필터 값들
        'search_field': search_field,
        'search_value': search_value,
        'user_type': user_type,
        'status': status,
        'start_date': start_date,
        'end_date': end_date,
        'per_page': per_page,
        'sort_by': sort_by,
        
        # 추가 정보
        'total_count': queryset.count(),
    }
    
    return render(request, "dashboard/member_list.html", context)


def member_bulk_action(request):
    """
    🎯 회원 벌크 액션 처리 (AJAX)
    - 벌크 삭제
    - 벌크 상태 변경
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    action = request.POST.get('action')
    member_ids = request.POST.getlist('member_ids[]')
    
    if not member_ids:
        return JsonResponse({'success': False, 'message': '선택된 회원이 없습니다.'})
    
    try:
        if action == 'delete':
            # 회원 삭제 (실제로는 soft delete 권장)
            deleted_count = Member.objects.filter(id__in=member_ids).delete()[0]
            return JsonResponse({
                'success': True, 
                'message': f'{deleted_count}명의 회원이 삭제되었습니다.'
            })
            
        elif action == 'deactivate':
            # 회원 비활성화
            updated_count = Member.objects.filter(id__in=member_ids).update(is_active=False)
            return JsonResponse({
                'success': True, 
                'message': f'{updated_count}명의 회원이 비활성화되었습니다.'
            })
            
        elif action == 'activate':
            # 회원 활성화
            updated_count = Member.objects.filter(id__in=member_ids).update(is_active=True)
            return JsonResponse({
                'success': True, 
                'message': f'{updated_count}명의 회원이 활성화되었습니다.'
            })
            
        else:
            return JsonResponse({'success': False, 'message': '알 수 없는 액션입니다.'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'처리 중 오류가 발생했습니다: {str(e)}'})


def member_delete(request, member_id):
    """
    🎯 개별 회원 삭제 (AJAX)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        member = Member.objects.get(id=member_id)
        member_name = member.username or member.name or f"ID:{member_id}"
        
        # 실제로는 soft delete 권장
        member.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'회원 "{member_name}"이(가) 삭제되었습니다.'
        })
        
    except Member.DoesNotExist:
        return JsonResponse({'success': False, 'message': '존재하지 않는 회원입니다.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'삭제 중 오류가 발생했습니다: {str(e)}'})


def get_member_stats(request):
    """
    🎯 회원 통계 정보 (AJAX)
    - 대시보드나 요약 정보용
    """
    try:
        stats = {
            'total_members': Member.objects.count(),
            'active_members': Member.objects.filter(is_active=True).count(),
            'inactive_members': Member.objects.filter(is_active=False).count(),
            'new_members_today': Member.objects.filter(
                created_at__date=datetime.now().date()
            ).count(),
            'new_members_week': Member.objects.filter(
                created_at__date__gte=datetime.now().date() - timedelta(days=7)
            ).count(),
        }
        
        return JsonResponse({'success': True, 'stats': stats})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# ✅ 향후 추가 기능들
def member_detail(request, member_id):
    """회원 상세보기 (향후 구현)"""
    pass

def member_edit(request, member_id):
    """회원 정보 수정 (향후 구현)"""
    pass

def member_export_excel(request):
    """회원 목록 엑셀 다운로드 (향후 구현)"""
    pass