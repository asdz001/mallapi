# members/views/deleted_member_list.py
# ------------------------------------------------------------
# 목적: 삭제된 회원 관리 페이지
# UI: AdminLTE/Bootstrap 기반 (복구/완전삭제 기능)
# ------------------------------------------------------------

from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from members.models import Member

# ✅ 삭제 회원 테이블 컬럼 정의
DELETED_COLUMNS = [
    {
        "field": "username",
        "header": "아이디",
        "type": "text",
        "align": "left",
        "width": "120px",
        "truncate": 15,
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
        "field": "deleted_at",
        "header": "삭제일시",
        "type": "date",
        "align": "center",
        "width": "120px",
        "format": "Y-m-d H:i",
    },
    {
        "field": "deleted_by",
        "header": "삭제자",
        "type": "text",
        "align": "center",
        "width": "100px",
        "default": "시스템",
    },
    {
        "field": "delete_type",
        "header": "삭제유형",
        "type": "choice",
        "align": "center",
        "width": "100px",
    },
    {
        "field": "delete_reason",
        "header": "삭제사유",
        "type": "text",
        "align": "left",
        "width": "200px",
        "truncate": 30,
        "default": "사유없음",
    },
    {
        "field": "days_until_permanent_deletion",
        "header": "남은일수",
        "type": "number",
        "align": "center",
        "width": "80px",
    },
    {
        "field": "can_restore",
        "header": "복구가능",
        "type": "choice",
        "align": "center",
        "width": "80px",
    },
]

# ✅ 검색 필드 옵션
DELETED_SEARCH_FIELDS = [
    ("username", "아이디"),
    ("name", "이름"),
    ("email", "이메일"),
    ("deleted_by", "삭제자"),
    ("delete_reason", "삭제사유"),
]

# ✅ 삭제 유형 선택지
DELETE_TYPE_CHOICES = [
    ("", "전체"),
    ("admin_delete", "관리자 삭제"),
    ("self_withdrawal", "회원 탈퇴"),
    ("auto_cleanup", "자동 정리"),
    ("policy_violation", "정책 위반"),
]

# ✅ 복구 가능 여부 선택지
RESTORE_STATUS_CHOICES = [
    ("", "전체"),
    ("restorable", "복구가능"),
    ("expired", "기한만료"),
    ("blocked", "복구불가"),
]

# ✅ 페이지당 표시 옵션
PER_PAGE_OPTIONS = [10, 25, 50, 100]


def deleted_member_list(request):
    """
    삭제된 회원 목록 뷰
    - 검색/필터/정렬/페이지네이션을 처리해서 템플릿에 전달
    """
    # 📊 기본 쿼리셋 (삭제된 회원만)
    queryset = Member.deleted_objects.all()

    # 🔍 검색/필터 파라미터 수집
    search_field = request.GET.get("search_field", "username")
    search_value = request.GET.get("search_value", "").strip()
    delete_type = request.GET.get("delete_type", "")
    restore_status = request.GET.get("restore_status", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")

    # 🔎 기본 검색 적용 (선택된 필드 기준 부분일치)
    if search_value:
        if search_field == "username":
            queryset = queryset.filter(username__icontains=search_value)
        elif search_field == "name":
            queryset = queryset.filter(name__icontains=search_value)
        elif search_field == "email":
            queryset = queryset.filter(email__icontains=search_value)
        elif search_field == "deleted_by":
            queryset = queryset.filter(deleted_by__icontains=search_value)
        elif search_field == "delete_reason":
            queryset = queryset.filter(delete_reason__icontains=search_value)

    # 🔎 삭제 유형 필터
    if delete_type:
        queryset = queryset.filter(delete_type=delete_type)

    # 🔎 복구 가능 여부 필터
    if restore_status:
        now = timezone.now()
        if restore_status == "restorable":
            # 복구 가능: can_restore=True AND 기한 내
            queryset = queryset.filter(
                can_restore=True,
                restore_deadline__gt=now
            )
        elif restore_status == "expired":
            # 기한 만료: 기한이 지났지만 아직 완전삭제되지 않음
            queryset = queryset.filter(restore_deadline__lt=now)
        elif restore_status == "blocked":
            # 복구 불가: can_restore=False
            queryset = queryset.filter(can_restore=False)

    # 🔎 삭제일 범위 필터
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            queryset = queryset.filter(deleted_at__date__gte=start_date_obj)
        except ValueError:
            pass

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            queryset = queryset.filter(deleted_at__date__lte=end_date_obj)
        except ValueError:
            pass

    # ↕️ 정렬 (기본: 최신 삭제순)
    sort_by = request.GET.get("sort", "-deleted_at")
    valid_sort_fields = [
        "username", "-username",
        "name", "-name",
        "deleted_at", "-deleted_at",
        "deleted_by", "-deleted_by",
        "delete_type", "-delete_type",
        "restore_deadline", "-restore_deadline",
    ]
    queryset = queryset.order_by(sort_by) if sort_by in valid_sort_fields else queryset.order_by("-deleted_at")

    # 📄 페이지네이션
    try:
        per_page = int(request.GET.get("per_page", 25))
    except ValueError:
        per_page = 25
    if per_page not in PER_PAGE_OPTIONS:
        per_page = 25

    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page", 1)
    try:
        deleted_members = paginator.get_page(page_number)
    except Exception:
        deleted_members = paginator.get_page(1)

    # 📦 템플릿 컨텍스트
    context = {
        # 테이블 데이터
        "columns": DELETED_COLUMNS,
        "deleted_members": deleted_members,
        # 검색/필터 옵션
        "search_fields": DELETED_SEARCH_FIELDS,
        "delete_type_choices": DELETE_TYPE_CHOICES,
        "restore_status_choices": RESTORE_STATUS_CHOICES,
        "per_page_options": PER_PAGE_OPTIONS,
        # 현재 값 유지
        "search_field": search_field,
        "search_value": search_value,
        "delete_type": delete_type,
        "restore_status": restore_status,
        "start_date": start_date,
        "end_date": end_date,
        "per_page": per_page,
        "sort_by": sort_by,
        # 부가 정보
        "total_count": queryset.count(),
        # 통계 정보
        "stats": get_deleted_member_stats(),
    }
    return render(request, "dashboard/deleted_member_list.html", context)


def restore_member(request, member_id):
    """
    삭제된 회원 복구 (AJAX)
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "잘못된 요청입니다."})

    try:
        # 삭제된 회원만 조회
        member = Member.deleted_objects.get(id=member_id)
        
        if not member.can_be_restored():
            if not member.can_restore:
                return JsonResponse({"success": False, "message": "복구할 수 없는 회원입니다."})
            else:
                return JsonResponse({"success": False, "message": "복구 기한이 만료되었습니다."})
        
        member_name = member.username or member.name or f"ID:{member_id}"
        admin_user = request.user.username if hasattr(request.user, 'username') else 'admin'
        
        # 회원 복구 실행
        member.restore(restored_by=admin_user)
        
        return JsonResponse({
            "success": True, 
            "message": f'회원 "{member_name}"이(가) 복구되었습니다.',
            "member_name": member_name
        })

    except Member.DoesNotExist:
        return JsonResponse({"success": False, "message": "존재하지 않는 삭제 회원입니다."})
    except ValueError as e:
        return JsonResponse({"success": False, "message": str(e)})
    except Exception as e:
        return JsonResponse({"success": False, "message": f"복구 중 오류가 발생했습니다: {str(e)}"})


def permanent_delete_member(request, member_id):
    """
    회원 완전 삭제 (AJAX) - 되돌릴 수 없음
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "잘못된 요청입니다."})

    try:
        # 삭제된 회원만 조회
        member = Member.deleted_objects.get(id=member_id)
        member_name = member.username or member.name or f"ID:{member_id}"
        
        # 완전 삭제 실행
        member.permanent_delete()
        
        return JsonResponse({
            "success": True, 
            "message": f'회원 "{member_name}"이(가) 완전히 삭제되었습니다.',
            "member_name": member_name
        })

    except Member.DoesNotExist:
        return JsonResponse({"success": False, "message": "존재하지 않는 삭제 회원입니다."})
    except ValueError as e:
        return JsonResponse({"success": False, "message": str(e)})
    except Exception as e:
        return JsonResponse({"success": False, "message": f"완전삭제 중 오류가 발생했습니다: {str(e)}"})


def bulk_restore_members(request):
    """
    삭제된 회원 벌크 복구 (AJAX)
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "잘못된 요청입니다."})

    member_ids = request.POST.getlist("member_ids[]")
    
    if not member_ids:
        return JsonResponse({"success": False, "message": "선택된 회원이 없습니다."})

    try:
        admin_user = request.user.username if hasattr(request.user, 'username') else 'admin'
        restored_count = 0
        failed_count = 0
        
        # 복구 가능한 삭제된 회원들만 대상
        members = Member.deleted_objects.filter(id__in=member_ids)
        for member in members:
            try:
                if member.can_be_restored():
                    member.restore(restored_by=admin_user)
                    restored_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1
        
        message = f"{restored_count}명의 회원이 복구되었습니다."
        if failed_count > 0:
            message += f" ({failed_count}명은 복구할 수 없어 제외되었습니다.)"
        
        return JsonResponse({
            "success": True, 
            "message": message,
            "restored_count": restored_count,
            "failed_count": failed_count
        })

    except Exception as e:
        return JsonResponse({"success": False, "message": f"벌크 복구 중 오류가 발생했습니다: {str(e)}"})


def bulk_permanent_delete_members(request):
    """
    삭제된 회원 벌크 완전삭제 (AJAX) - 매우 위험한 작업
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "잘못된 요청입니다."})

    member_ids = request.POST.getlist("member_ids[]")
    confirm_text = request.POST.get("confirm_text", "").strip()
    
    if not member_ids:
        return JsonResponse({"success": False, "message": "선택된 회원이 없습니다."})
    
    # 🚨 안전 장치: 확인 텍스트 검증
    if confirm_text != "영구삭제":
        return JsonResponse({"success": False, "message": "확인 텍스트를 정확히 입력해주세요."})

    try:
        deleted_count = 0
        
        # 삭제된 회원들만 대상으로 완전삭제
        members = Member.deleted_objects.filter(id__in=member_ids)
        for member in members:
            try:
                member.permanent_delete()
                deleted_count += 1
            except Exception:
                pass  # 개별 실패는 무시하고 계속 진행
        
        return JsonResponse({
            "success": True, 
            "message": f"{deleted_count}명의 회원이 완전히 삭제되었습니다.",
            "deleted_count": deleted_count
        })

    except Exception as e:
        return JsonResponse({"success": False, "message": f"벌크 완전삭제 중 오류가 발생했습니다: {str(e)}"})


def get_deleted_member_stats():
    """삭제 회원 통계 정보"""
    try:
        now = timezone.now()
        
        stats = {
            "total_deleted": Member.deleted_objects.count(),
            "admin_deleted": Member.deleted_objects.filter(delete_type='admin_delete').count(),
            "self_withdrawal": Member.deleted_objects.filter(delete_type='self_withdrawal').count(),
            "restorable": Member.deleted_objects.filter(
                can_restore=True,
                restore_deadline__gt=now
            ).count(),
            "expired": Member.deleted_objects.filter(restore_deadline__lt=now).count(),
            "today_deleted": Member.deleted_objects.filter(deleted_at__date=datetime.now().date()).count(),
        }
        return stats
    except Exception:
        return {
            "total_deleted": 0,
            "admin_deleted": 0,
            "self_withdrawal": 0,
            "restorable": 0,
            "expired": 0,
            "today_deleted": 0,
        }


# ✅ 자동 정리 작업용 (향후 크론잡에서 호출)
def auto_cleanup_expired_members():
    """
    복구 기한이 지난 회원들 자동 완전삭제
    - 크론잡이나 celery 등에서 주기적으로 실행
    """
    try:
        now = timezone.now()
        expired_members = Member.deleted_objects.filter(
            restore_deadline__lt=now,
            can_restore=True  # 복구 가능했던 회원들만
        )
        
        deleted_count = 0
        for member in expired_members:
            try:
                member.permanent_delete()
                deleted_count += 1
            except Exception:
                pass
        
        return deleted_count
    except Exception:
        return 0