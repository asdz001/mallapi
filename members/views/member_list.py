# dashboard/views/members/member_list.py
# ------------------------------------------------------------
# 회원 목록 뷰
# - 템플릿과의 파라미터/컨텍스트 이름을 "호환"하도록 정리
# - 등급 컬럼/필터 추가 (select_related('grade')로 N+1 방지)
# - 소프트 삭제/벌크 액션/개별 삭제 API 포함 (urls.py 연결)
# ------------------------------------------------------------

from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from members.models import Member

# ✅ 테이블 컬럼 정의 (템플릿의 table_filters와 호환되는 구조)
#    - field 값은 "모델 필드명"과 정확히 일치해야 함
#    - ⚠️ 중복되었던 member_type 컬럼은 1개만 유지
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
        "type": "grade",  # 커스텀 표시(배지)
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

# ✅ 회원유형/상태 선택지 (템플릿 select에 사용)
USER_TYPE_CHOICES = [
    ("", "전체"),
    ("B2C", "일반회원"),
    ("B2B", "사업자회원"),
]
STATUS_CHOICES = [
    ("", "전체"),
    ("active", "활성"),
    ("inactive", "비활성"),
]

# ✅ 페이지당 표시 옵션
PER_PAGE_OPTIONS = [10, 25, 50, 100]


def member_list(request):
    """
    운영자 - 회원 목록
    - 템플릿 파라미터 이름을 '그대로' 받되(호환), 내부에서는 정규화하여 필터 적용
      * 검색어: search_value 또는 search_query
      * 회원유형: user_type 또는 member_type
      * 상태: status(active/inactive) 또는 is_active(true/false)
      * 등급: grade 또는 grade_filter
    """
    # 0) 기본 쿼리 (활성 회원만: ActiveMemberManager) + 등급 조인
    members_qs = Member.objects.select_related("grade").all()

    # 1) 파라미터 호환 수신
    search_field = request.GET.get("search_field", "username")
    # 템플릿은 search_value를 사용 → 우선 사용, 없으면 search_query 백업
    search_query = (request.GET.get("search_value") or request.GET.get("search_query") or "").strip()

    # 유형/상태 명칭 호환
    raw_user_type = request.GET.get("user_type")
    raw_member_type = request.GET.get("member_type")
    member_type_filter = (raw_member_type or raw_user_type or "").strip()

    raw_status = (request.GET.get("status") or request.GET.get("is_active") or "").strip().lower()
    # 등급 필터(숫자 id 또는 'none')
    grade_filter = (request.GET.get("grade") or request.GET.get("grade_filter") or "").strip()

    # 2) 등급 필터
    if grade_filter:
        if grade_filter == "none":
            members_qs = members_qs.filter(grade__isnull=True)
        else:
            members_qs = members_qs.filter(grade_id=grade_filter)

    # 3) 검색
    if search_query and search_field:
        if search_field == "username":
            members_qs = members_qs.filter(username__icontains=search_query)
        elif search_field == "name":
            members_qs = members_qs.filter(name__icontains=search_query)
        elif search_field == "email":
            members_qs = members_qs.filter(email__icontains=search_query)
        elif search_field == "phone":
            members_qs = members_qs.filter(phone__icontains=search_query)

    # 4) 회원유형 필터
    if member_type_filter:
        members_qs = members_qs.filter(member_type=member_type_filter)

    # 5) 상태 필터 (둘 다 호환)
    # - status: 'active'/'inactive'
    # - is_active: 'true'/'false'
    if raw_status in ("active", "inactive", "true", "false"):
        active_bool = raw_status in ("active", "true")
        members_qs = members_qs.filter(is_active=active_bool)

    # 6) 정렬(필요 시 확장)
    members_qs = members_qs.order_by("-created_at")

    # 7) 페이지네이션
    per_page = min(int(request.GET.get("per_page", 20)), 100)
    paginator = Paginator(members_qs, per_page)
    page = request.GET.get("page", 1)
    members = paginator.get_page(page)

    # 8) 등급 목록(필터용)
    from members.models import MemberGrade
    grades = MemberGrade.objects.filter(is_active=True).order_by("member_type", "order")

    # 9) 템플릿 컨텍스트 (기존 이름도 함께 내려 호환 보장)
    context = {
        "members": members,
        "columns": COLUMNS,

        # 검색/필터 옵션들
        "search_fields": SEARCH_FIELDS,
        "user_type_choices": USER_TYPE_CHOICES,
        "status_choices": STATUS_CHOICES,
        "per_page_options": PER_PAGE_OPTIONS,

        # 현재 선택 상태(양쪽 키 모두 제공)
        "search_field": search_field,
        "search_query": search_query,
        "search_value": search_query,     # 🔁 템플릿 호환
        "member_type_filter": member_type_filter,
        "user_type": member_type_filter,  # 🔁 템플릿 호환
        "is_active_filter": raw_status,
        "status": raw_status,             # 🔁 템플릿 호환
        "grades": grades,
        "grade_filter": grade_filter,
        "grade": grade_filter,            # 🔁 템플릿 호환

        # 일부 include에서 요구할 수 있는 값(없어도 되지만 안전장치)
        "sort_choices": [],
        "per_page": per_page,
    }
    return render(request, "dashboard/member/member_list.html", context)


def member_bulk_action(request):
    """
    회원 벌크 액션 (AJAX) - 소프트 삭제/활성화/비활성화
    urls.py: path('bulk-action', member_list.member_bulk_action, name='member_bulk_action')
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
            # 🔧 소프트 삭제로 변경(사유 필수)
            if not delete_reason:
                return JsonResponse({"success": False, "message": "삭제 사유를 입력해주세요."})

            deleted_count = 0
            admin_user = request.user.username if hasattr(request.user, "username") else "admin"

            # 활성 회원들만 대상으로 소프트 삭제 실행 (Member.objects는 활성 회원 매니저)
            members = Member.objects.filter(id__in=member_ids)
            for member in members:
                if not member.is_deleted:
                    member.soft_delete(
                        deleted_by=admin_user,
                        reason=delete_reason,
                        delete_type="admin_delete",
                    )
                    deleted_count += 1

            return JsonResponse(
                {"success": True, "message": f"{deleted_count}명의 회원이 삭제되었습니다.", "deleted_count": deleted_count}
            )

        elif action == "deactivate":
            updated_count = Member.objects.filter(id__in=member_ids).update(is_active=False)
            return JsonResponse({"success": True, "message": f"{updated_count}명의 회원이 비활성화되었습니다."})

        elif action == "activate":
            updated_count = Member.objects.filter(id__in=member_ids).update(is_active=True)
            return JsonResponse({"success": True, "message": f"{updated_count}명의 회원이 활성화되었습니다."})

        else:
            return JsonResponse({"success": False, "message": "알 수 없는 액션입니다."})

    except Exception as e:
        return JsonResponse({"success": False, "message": f"처리 중 오류가 발생했습니다: {str(e)}"})


def member_delete(request, member_id):
    """
    개별 회원 소프트 삭제 (AJAX)
    urls.py: path('delete/<int:member_id>', member_list.member_delete, name='member_delete')
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "잘못된 요청입니다."})

    try:
        member = Member.objects.get(id=member_id)  # 활성 회원 매니저
        if member.is_deleted:
            return JsonResponse({"success": False, "message": "이미 삭제된 회원입니다."})

        delete_reason = request.POST.get("delete_reason", "").strip()
        if not delete_reason:
            return JsonResponse({"success": False, "message": "삭제 사유를 입력해주세요."})

        member_name = member.username or member.name or f"ID:{member_id}"
        admin_user = request.user.username if hasattr(request.user, "username") else "admin"

        member.soft_delete(
            deleted_by=admin_user,
            reason=delete_reason,
            delete_type="admin_delete",
        )

        return JsonResponse({"success": True, "message": f'회원 "{member_name}"이(가) 삭제되었습니다.', "member_name": member_name})

    except Member.DoesNotExist:
        return JsonResponse({"success": False, "message": "존재하지 않는 회원입니다."})
    except Exception as e:
        return JsonResponse({"success": False, "message": f"삭제 중 오류가 발생했습니다: {str(e)}"})
