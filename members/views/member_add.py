# members/views/member_add.py
# ------------------------------------------------------------
# 목적: 회원 추가 화면(GET) + 저장 처리(POST)
# UI: AdminLTE/Bootstrap 기반 탭 구조 (템플릿에서 구성)
# ------------------------------------------------------------

from django.shortcuts import render, redirect
from django.contrib import messages

from members.forms import MemberCreateForm


def member_add(request):
    """
    회원 추가 화면 & 저장 처리
    - GET: 빈 폼 표시
    - POST: 검증 후 저장 → (선택) 다시 추가 페이지 or 목록으로 이동
    """
    if request.method == "POST":
        form = MemberCreateForm(request.POST)
        if form.is_valid():
            member = form.save()
            messages.success(request, f"회원 '{member.username}' 이(가) 등록되었습니다.")
            # 🔁 다시 추가 페이지로 (빈 폼)
            return redirect('dashboard:member_add')
            # 📄 목록으로 보내고 싶으면 위 대신 아래 한 줄:
            # return redirect('dashboard:member_list')
        else:
            messages.error(request, "입력값을 다시 확인해 주세요.")
    else:
        form = MemberCreateForm()

    context = {"form": form}
    return render(request, "dashboard/member_add.html", context)
