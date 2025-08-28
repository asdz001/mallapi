# dashboard/views/members/member_list.py

from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from members.models import Member

# ✅ 테이블 컬럼 정의 (템플릿의 table_filters와 호환되는 구조)
#    - field 값은 "모델 필드명"과 정확히 일치해야 함
COLUMNS = [
    {
        "field": "username",
        "header": "아이디",
        "type": "text",
        "align": "left",
        "width": "120px",
        "truncate": 15,  # 너무 긴 값은 줄임 표시
    },
    {
        "field": "name",
        "header": "이름",
        "type": "text",
        "align": "center",
        "width": "100px",
        "default": "미입력",
    },
    {
        "field": "grade",
        "header": "등급",
        "type": "grade",  # 새로운 타입
        "align": "center",
        "width": "100px",
        "default": "등급없음",
    },
    {
        "field": "member_type",
        "header": "회원유형",
        "type": "choice",
        "align": "center",
        "width": "90px",
        "default": "일반",
    },
    {
        "field": "member_type",  # 🔁 user_type → member_type
        "header": "회원유형",
        "type": "choice",
        "align": "center",
        "width": "90px",
        "default": "일반",
    },
    {
        "field": "email",
        "header": "이메일",
        "type": "text",
        "align": "left",
        "width": "200px",
        "truncate": 25,
        "default": "미입력",
    },
    {
        "field": "phone",  # 🔁 mobile → phone
        "header": "휴대폰",
        "type": "text",
        "align": "center",
        "width": "120px",
        "default": "미입력",
    },
    {
        "field": "gender",
        "header": "성별",
        "type": "choice",
        "align": "center",
        "width": "70px",
        "default": "미입력",
    },
    {
        "field": "birth_date",  # 🔁 birthdate → birth_date
        "header": "생년월일",
        "type": "date",
        "align": "center",
        "width": "100px",
        "format": "Y-m-d",
        "default": "미입력",
    },
    {
        "field": "created_at",
        "header": "가입일",
        "type": "date",
        "align": "center",
        "width": "120px",
        "format": "Y-m-d H:i",
    },
    {
        "field": "is_active",
        "header": "상태",
        "type": "choice",
        "align": "center",
        "width": "20px",
    },
]

# ✅ 검색 필드 옵션 (화면의 검색 셀렉트에 노출)
SEARCH_FIELDS = [
    ("username", "아이디"),
    ("name", "이름"),
    ("email", "이메일"),
    ("phone", "휴대폰"),  # 🔁 mobile → phone
]

# ✅ 회원유형 선택지 (모델의 choices와 일치해야 필터가 동작)
USER_TYPE_CHOICES = [
    ("", "전체"),
    ("B2C", "일반회원"),
    ("B2B", "사업자회원"),
]

# ✅ 상태 선택지
STATUS_CHOICES = [
    ("", "전체"),
    ("active", "활성"),
    ("inactive", "비활성"),
]

# ✅ 페이지당 표시 옵션
PER_PAGE_OPTIONS = [10, 25, 50, 100]


#member_list 뷰 함수 수정 (기존 함수 내용 일부 수정)
def member_list(request):
    # 🆕 등급 관련 데이터를 포함하여 쿼리 (select_related 추가)
    members_qs = Member.objects.select_related('grade').all()
    
    # 기존 검색 및 필터링...
    search_field = request.GET.get('search_field', 'username')
    search_query = request.GET.get('search_query', '').strip()
    member_type_filter = request.GET.get('member_type')
    is_active_filter = request.GET.get('is_active')
    
    # 🆕 등급 필터링 추가
    grade_filter = request.GET.get('grade')
    if grade_filter:
        if grade_filter == 'none':  # 등급 없음
            members_qs = members_qs.filter(grade__isnull=True)
        else:
            members_qs = members_qs.filter(grade_id=grade_filter)
    
    # 기존 필터링 로직들...
    if search_query and search_field:
        if search_field == 'username':
            members_qs = members_qs.filter(username__icontains=search_query)
        elif search_field == 'name':
            members_qs = members_qs.filter(name__icontains=search_query)
        elif search_field == 'email':
            members_qs = members_qs.filter(email__icontains=search_query)
        elif search_field == 'phone':
            members_qs = members_qs.filter(phone__icontains=search_query)
    
    if member_type_filter:
        members_qs = members_qs.filter(member_type=member_type_filter)
    
    if is_active_filter:
        members_qs = members_qs.filter(is_active=(is_active_filter == 'true'))

    # 페이지네이션
    per_page = min(int(request.GET.get('per_page', 20)), 100)
    paginator = Paginator(members_qs, per_page)
    page = request.GET.get('page', 1)
    members = paginator.get_page(page)

    # 🆕 등급 목록을 템플릿에 전달 (필터용)
    from members.models import MemberGrade
    grades = MemberGrade.objects.filter(is_active=True).order_by('member_type', 'order')

    # 검색 필드 옵션
    search_fields = [
        ('username', '아이디'),
        ('name', '이름'),
        ('email', '이메일'),
        ('phone', '휴대폰'),
    ]

    context = {
        'members': members,
        'columns': COLUMNS,
        'search_fields': search_fields,
        'search_field': search_field,
        'search_query': search_query,
        'member_type_filter': member_type_filter,
        'is_active_filter': is_active_filter,
        'grades': grades,  # 🆕 등급 목록 추가
        'grade_filter': grade_filter,  # 🆕 현재 선택된 등급 필터
        'per_page': per_page,
    }

    return render(request, 'dashboard/member/member_list.html', context)


def member_bulk_action(request):
    """
    회원 벌크 액션 (AJAX) - 소프트 삭제 방식으로 변경
    - delete: 선택 회원 소프트 삭제
    - deactivate: 비활성화
    - activate: 활성화
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "잘못된 요청입니다."})

    action = request.POST.get("action")
    member_ids = request.POST.getlist("member_ids[]")
    delete_reason = request.POST.get("delete_reason", "").strip()
    
    if not member_ids:
        return JsonResponse({"success": False, "message": "선택된 회원이 없습니다."})

    try:
        if action == "delete":
            # 🔧 소프트 삭제로 변경
            if not delete_reason:
                return JsonResponse({"success": False, "message": "삭제 사유를 입력해주세요."})
            
            deleted_count = 0
            admin_user = request.user.username if hasattr(request.user, 'username') else 'admin'
            
            # 활성 회원들만 대상으로 소프트 삭제 실행
            members = Member.objects.filter(id__in=member_ids)  # objects 매니저로 이미 활성 회원만 조회됨
            for member in members:
                if not member.is_deleted:  # 추가 안전장치
                    member.soft_delete(
                        deleted_by=admin_user,
                        reason=delete_reason,
                        delete_type='admin_delete'
                    )
                    deleted_count += 1
            
            return JsonResponse({
                "success": True, 
                "message": f"{deleted_count}명의 회원이 삭제되었습니다.",
                "deleted_count": deleted_count
            })

        elif action == "deactivate":
            # 활성 회원만 비활성화
            updated_count = Member.objects.filter(id__in=member_ids).update(is_active=False)
            return JsonResponse({"success": True, "message": f"{updated_count}명의 회원이 비활성화되었습니다."})

        elif action == "activate":
            # 활성 회원만 활성화
            updated_count = Member.objects.filter(id__in=member_ids).update(is_active=True)
            return JsonResponse({"success": True, "message": f"{updated_count}명의 회원이 활성화되었습니다."})

        else:
            return JsonResponse({"success": False, "message": "알 수 없는 액션입니다."})

    except Exception as e:
        return JsonResponse({"success": False, "message": f"처리 중 오류가 발생했습니다: {str(e)}"})


def member_delete(request, member_id):
    """
    개별 회원 소프트 삭제 (AJAX)
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "잘못된 요청입니다."})

    try:
        # 활성 회원만 조회 (objects 매니저 사용)
        member = Member.objects.get(id=member_id)
        
        if member.is_deleted:
            return JsonResponse({"success": False, "message": "이미 삭제된 회원입니다."})
        
        # 삭제 사유 확인
        delete_reason = request.POST.get("delete_reason", "").strip()
        if not delete_reason:
            return JsonResponse({"success": False, "message": "삭제 사유를 입력해주세요."})
        
        member_name = member.username or member.name or f"ID:{member_id}"
        admin_user = request.user.username if hasattr(request.user, 'username') else 'admin'
        
        # 소프트 삭제 실행
        member.soft_delete(
            deleted_by=admin_user,
            reason=delete_reason,
            delete_type='admin_delete'
        )
        
        return JsonResponse({
            "success": True, 
            "message": f'회원 "{member_name}"이(가) 삭제되었습니다.',
            "member_name": member_name
        })

    except Member.DoesNotExist:
        return JsonResponse({"success": False, "message": "존재하지 않는 회원입니다."})
    except Exception as e:
        return JsonResponse({"success": False, "message": f"삭제 중 오류가 발생했습니다: {str(e)}"})


def get_member_stats(request):
    """
    회원 통계 (대시보드 요약용, AJAX) - 활성 회원 기준
    """
    try:
        stats = {
            "total_members": Member.objects.count(),  # 활성 회원 수
            "active_members": Member.objects.filter(is_active=True).count(),
            "inactive_members": Member.objects.filter(is_active=False).count(),
            "new_members_today": Member.objects.filter(created_at__date=datetime.now().date()).count(),
            "new_members_week": Member.objects.filter(
                created_at__date__gte=datetime.now().date() - timedelta(days=7)
            ).count(),
            # 🆕 삭제 관련 통계 추가
            "deleted_members": Member.deleted_objects.count(),  # 삭제된 회원 수
        }
        return JsonResponse({"success": True, "stats": stats})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})


# ✅ 향후 추가 예정(상세/수정/엑셀)
def member_detail(request, member_id):
    """회원 상세보기 (향후 구현)"""
    pass


def member_edit(request, member_id):
    """회원 정보 수정 (향후 구현)"""
    pass


def member_export_excel(request):
    """회원 목록 엑셀 다운로드 (향후 구현)"""
    pass