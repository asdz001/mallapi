# mall_settings/views/operator_crud.py

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.contrib.auth import update_session_auth_hash
from mall_settings.models import OperatorProfile
from mall_settings.forms import OperatorForm




# ✅ 상세 조회
@require_http_methods(["GET"])
def operator_detail_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile = getattr(user, 'operatorprofile', None)

    data = {
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'email': user.email,
        'contact_number': profile.contact_number if profile else '',
        'receive_order_alerts': profile.receive_order_alerts if profile else False,
        'receive_stock_alerts': profile.receive_stock_alerts if profile else False,
        'allowed_retailers': list(profile.allowed_retailers.values_list('id', flat=True)) if profile else [],
    }
    return JsonResponse({'success': True, 'data': data})


# ✅ 생성
@require_http_methods(["POST"])
def operator_create_view(request):
    form = OperatorForm(request.POST)
    if form.is_valid():
        user = form.save(commit=False)
        password = form.cleaned_data.get('password')
        if password:
            user.set_password(password)

        user.is_staff = True    
        user.save()

        profile = OperatorProfile.objects.create(
            user=user,
            contact_number=form.cleaned_data.get('contact_number'),
            receive_order_alerts=form.cleaned_data.get('receive_order_alerts'),
            receive_stock_alerts=form.cleaned_data.get('receive_stock_alerts')
        )
        profile.allowed_retailers.set(form.cleaned_data.get('allowed_retailers'))
        return JsonResponse({'success': True, 'message': '운영자가 등록되었습니다.'})
    else:
        print("폼 에러:", form.errors)  # 👈 이거 한 줄 추가
        return JsonResponse({'success': False, 'message': '입력값이 유효하지 않습니다.', 'errors': form.errors})


#✅ 운영자 수정
@require_http_methods(["POST"])
def operator_update_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile, _ = OperatorProfile.objects.get_or_create(user=user)

    form = OperatorForm(request.POST, instance=user, user_instance=user)

    if form.is_valid():
        user = form.save(commit=False, user_instance=user)

        # ✅ 비밀번호가 입력된 경우에만 비밀번호 변경
        password = form.cleaned_data.get('password')
        if password and password.strip():
            user.set_password(password)
            update_session_auth_hash(request, user)  # ⛔ 변경 시 세션 유지

        user.save()

        # ✅ OperatorProfile 정보 업데이트
        profile.contact_number = form.cleaned_data.get('contact_number')
        profile.receive_order_alerts = form.cleaned_data.get('receive_order_alerts')
        profile.receive_stock_alerts = form.cleaned_data.get('receive_stock_alerts')
        profile.allowed_retailers.set(form.cleaned_data.get('allowed_retailers'))
        profile.save()

        return JsonResponse({'success': True, 'message': '운영자 정보가 수정되었습니다.'})
    else:
        print(form.errors)
        return JsonResponse({'success': False, 'message': '수정 실패', 'errors': form.errors})


# ✅ 삭제
@require_http_methods(["POST"])
def operator_delete_view(request, pk):
    try:
        user = User.objects.get(pk=pk)
        user.delete()
        return JsonResponse({'success': True, 'message': '운영자가 삭제되었습니다.'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': '운영자를 찾을 수 없습니다.'})
