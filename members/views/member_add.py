# members/views/member_add.py
# ------------------------------------------------------------
# 회원 추가(가입) 화면 - 등급 선택 기능 강화
# - 회원 타입별 등급 목록 제공
# - 등급 선택 시 자동 이력 기록
# - 기본 등급 자동 설정 로직
# ------------------------------------------------------------

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db import models

# ✅ 프로젝트의 실제 폼/모델을 사용
from ..forms import MemberCreateForm
from ..models import Member, MemberGrade, MemberGradeHistory

@staff_member_required
def member_add(request):
    """운영자-회원 추가(가입)"""

    if request.method == "POST":
        form = MemberCreateForm(request.POST, request.FILES or None)

        if form.is_valid():
            # 1) 회원 저장(모델에서 기본 등급 자동 세팅이 수행됨)
            member: Member = form.save()

            # 2) 폼에 등급/고정이 노출되어 있다면 그 값을 우선 반영(있을 때만 처리)
            cleaned = getattr(form, "cleaned_data", {}) or {}
            selected_grade = cleaned.get("grade")
            grade_fixed = cleaned.get("grade_fixed")
            grade_fixed_reason = cleaned.get("grade_fixed_reason")

            # 2-1) 등급 반영(선택되어 있으면 우선)
            if selected_grade and isinstance(selected_grade, MemberGrade):
                # 등급 변경 + 이력 기록
                member.change_grade(
                    new_grade=selected_grade,
                    reason="manual",
                    changed_by=request.user,
                    reason_detail="가입 시 운영자 지정"
                )
            else:
                # 3) "가입 시 최초 등급 부여" 이력 기록
                try:
                    if member.grade:  # 기본 등급이 설정되어 있다면
                        # 기존 이력이 없는 경우에만 signup 이력 생성
                        if not MemberGradeHistory.objects.filter(member=member).exists():
                            MemberGradeHistory.objects.create(
                                member=member,
                                old_grade=None,
                                new_grade=member.grade,
                                change_reason="signup",
                                reason_detail="신규 가입 기본 등급 부여",
                                changed_by=request.user
                            )
                except Exception as e:
                    # 이력 기록 실패해도 가입은 성공으로 처리
                    print(f"등급 이력 기록 오류: {e}")

            # 2-2) 등급 "고정" 옵션 반영
            if grade_fixed:
                try:
                    member.fix_grade(
                        reason=grade_fixed_reason or "가입 시 등급 고정",
                        fixed_by=request.user
                    )
                except Exception as e:
                    print(f"등급 고정 설정 오류: {e}")

            messages.success(request, f"[{member.name or member.email}] 회원이 등록되었습니다.")
            
            # 👉 리스트로 이동
            return redirect("dashboard:member_list")

        else:
            # 유효성 에러 → 폼 그대로 재표시
            messages.error(request, "입력값을 다시 확인해주세요.")

    else:
        # GET: 빈 폼 생성
        form = MemberCreateForm()

    # ✅ 템플릿에 등급 정보 추가 제공
    context = {
        "form": form,
        "grades": _get_all_grades_for_template(),  # 템플릿에서 JS용으로 사용
    }
    
    return render(request, "dashboard/member/member_add.html", context)

def _get_all_grades_for_template():
    """
    템플릿에서 JavaScript로 사용할 등급 정보 반환
    - 회원 타입 변경 시 동적 필터링용
    """
    try:
        grades = MemberGrade.objects.filter(is_active=True).order_by('member_type', 'order', 'name')
        grades_data = []
        
        for grade in grades:
            grades_data.append({
                'id': grade.id,
                'name': grade.display_name or grade.name,
                'member_type': grade.member_type,
                'is_default': grade.is_default,
                'color': grade.color_code or '#6c757d',
                'icon': grade.icon_class or 'fas fa-user',
            })
            
        return grades_data
        
    except Exception as e:
        print(f"등급 목록 조회 오류: {e}")
        return []