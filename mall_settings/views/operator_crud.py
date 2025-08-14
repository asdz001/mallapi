# mall_settings/views/operator_crud.py
# ---------------------------------------------------------
# 운영자 CRUD 뷰
# - JSON 응답 구조 통일(success/message/errors)
# - 생성: 비밀번호 필수(무비번 계정 금지)
# - 수정: 비밀번호 비어있으면 '미변경'
# - 로그인 차단: is_active로 명시적 제어(체크 시에만 차단)
# - 치명적 오타 제거(과거 'return J' 잔재 제거)
# ---------------------------------------------------------

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.contrib.auth import update_session_auth_hash
from django.db import transaction

from mall_settings.models import OperatorProfile
from mall_settings.forms import OperatorForm


def _json_ok(message, **extra):
    """성공 응답(JSON) 통일"""
    data = {"success": True, "message": message}
    data.update(extra)
    return JsonResponse(data)


def _json_err(message, errors=None, status=400, **extra):
    """실패 응답(JSON) 통일"""
    data = {"success": False, "message": message}
    if errors:
        data["errors"] = errors
    data.update(extra)
    return JsonResponse(data, status=status)


# ✅ 상세 조회(프론트에서 모달 열 때 사용)
@require_http_methods(["GET"])
def operator_detail_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile, _ = OperatorProfile.objects.get_or_create(user=user)
    data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "is_active": user.is_active,
        "contact_number": profile.contact_number or "",
        "receive_order_alerts": profile.receive_order_alerts,
        "receive_stock_alerts": profile.receive_stock_alerts,
        "allowed_retailers": list(profile.allowed_retailers.values_list("id", flat=True)),
    }
    return _json_ok("조회 성공", data=data)


# ✅ 생성(Create) — 비밀번호 필수
@require_http_methods(["POST"])
@transaction.atomic
def operator_create_view(request):
    form = OperatorForm(request.POST)

    # 생성 시: 비밀번호 '필수' 체크(폼은 required=False 이므로 여기서 강제)
    pwd = request.POST.get("password", "").strip()
    pwd2 = request.POST.get("confirm_password", "").strip()
    if not pwd or not pwd2:
        return _json_err("비밀번호는 필수입니다. 비밀번호와 비밀번호 확인을 모두 입력해주세요.")

    if form.is_valid():
        try:
            user = form.save(commit=True, user_instance=None)

            # 운영자는 관리자 화면 접근을 위해 staff 권한 부여
            user.is_staff = True

            # 로그인 차단 체크(선택): disable_login/is_active 처리
            disable_login = request.POST.get("disable_login")
            if disable_login in ("1", "true", "on"):
                user.is_active = False
            else:
                user.is_active = True

            user.save()

            return _json_ok("운영자가 등록되었습니다.", id=user.id)
        except Exception as e:
            # 예외 발생 시 DB 롤백됨(transaction.atomic)
            return _json_err("생성 중 오류가 발생했습니다.", errors={"__all__": [str(e)]}, status=500)
    else:
        # 폼 에러 그대로 반환(프론트에서 표시)
        return _json_err("입력값이 유효하지 않습니다.", errors=form.errors)


# ✅ 수정(Update) — 비밀번호 비어있으면 '미변경'
@require_http_methods(["POST"])
@transaction.atomic
def operator_update_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    OperatorProfile.objects.get_or_create(user=user)

    # ★ 추가: POST 사본을 만들고, 비번 두 칸이 모두 빈칸이면 키 자체를 제거
    data = request.POST.copy()
    pwd = (data.get("password") or "").strip()
    pwd2 = (data.get("confirm_password") or "").strip()
    if not pwd and not pwd2:
        data.pop("password", None)
        data.pop("confirm_password", None)

    # 기존: request.POST 대신 data를 사용
    form = OperatorForm(data, user_instance=user, instance=user)

    if form.is_valid():
        try:
            # 폼에서 클린된 비번(입력된 경우에만 값이 있음)
            new_pwd = form.cleaned_data.get("password") or ""

            # 로그인 차단 → is_active 제어
            disable_login = data.get("disable_login")
            user.is_active = False if disable_login in ("1", "true", "on") else True

            # 저장 (user / profile / 거래처 권한까지 폼 save에 위임)
            user = form.save(commit=True, user_instance=user)

            # 비번이 실제 변경됐고, 본인 수정이면 세션 유지
            if new_pwd and request.user.pk == user.pk:
                update_session_auth_hash(request, user)

            return _json_ok("수정되었습니다.", id=user.id)
        except Exception as e:
            return _json_err("수정 중 오류가 발생했습니다.", errors={"__all__": [str(e)]}, status=500)
    else:
        return _json_err("수정 실패", errors=form.errors)


# ✅ 삭제(Delete)
@require_http_methods(["POST"])
@transaction.atomic
def operator_delete_view(request, pk):
    try:
        user = User.objects.get(pk=pk)
        user.delete()
        return _json_ok("운영자가 삭제되었습니다.")
    except User.DoesNotExist:
        return _json_err("운영자를 찾을 수 없습니다.", status=404)
    except Exception as e:
        return _json_err("삭제 중 오류가 발생했습니다.", errors={"__all__": [str(e)]}, status=500)
