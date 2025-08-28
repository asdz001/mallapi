# members/views/grade_views.py
# -----------------------------------------------------------------------------------
# 등급 관리 뷰
# - 기존 검색/필터/정렬/페이지네이션/통계 로직은 그대로 유지
# - grade_list: 컬럼 정의(GRADE_TABLE_COLUMNS) + 행 데이터(rows)까지 뷰에서 구성
# - 템플릿은 columns/rows 반복 출력만 담당하도록 단순화할 수 있음
# - 리다이렉트 네임스페이스를 dashboard로 통일
# -----------------------------------------------------------------------------------

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
from django.utils.html import format_html, escape  # ✅ 안전한 HTML/문자열 처리
from django.urls import reverse                   # ✅ URL 역참조 (네임스페이스 통일)
import json

from ..models import MemberGrade, Member, MemberGradeHistory
from django.contrib.auth.models import User


# -----------------------------------------------------------------------------------
# 테이블 컬럼 정의
#  - key:   rows[*]에서 읽을 키
#  - label: thead 표시 텍스트
#  - type:  셀 렌더링 타입(템플릿 분기 간소화용)
#  - align: 정렬 (선택)
# -----------------------------------------------------------------------------------
GRADE_TABLE_COLUMNS = [
    {"key": "grade_display", "label": "등급",   "type": "grade_display",     "align": "left"},
    {"key": "member_type",   "label": "타입",   "type": "member_type_badge", "align": "center"},
    {"key": "order",         "label": "순서",   "type": "text",              "align": "center"},
    {"key": "discount_rate", "label": "할인율", "type": "percent",           "align": "center"},
    {"key": "point_rate",    "label": "포인트", "type": "percent",           "align": "center"},
    {"key": "member_count",  "label": "회원수", "type": "number_badge",      "align": "center"},
    {"key": "is_active",     "label": "상태",   "type": "boolean_badge",     "align": "center"},
    {"key": "actions",       "label": "관리",   "type": "actions",           "align": "center"},
]


@staff_member_required
def grade_list(request):
    """
    등급 목록 조회
    - 기존 로직: 검색/필터/정렬/annotate/페이지네이션/통계 (원본과 동일)
    - 추가      : columns/rows를 구성하여 템플릿에서 동적 렌더 가능
    """

    # 1) 검색 및 필터링 (원본 유지) 【원본 근거】
    search = request.GET.get('search', '').strip()
    member_type_filter = request.GET.get('member_type', '')
    is_active_filter = request.GET.get('is_active', '')

    # 기본 쿼리셋 (원본)【:contentReference[oaicite:3]{index=3}】
    grades_qs = MemberGrade.objects.all()

    # 검색 조건 (원본)【:contentReference[oaicite:4]{index=4}】
    if search:
        grades_qs = grades_qs.filter(
            Q(name__icontains=search) |
            Q(display_name__icontains=search)
        )

    # 필터 조건 (원본)【:contentReference[oaicite:5]{index=5}】
    if member_type_filter:
        grades_qs = grades_qs.filter(member_type=member_type_filter)

    if is_active_filter:
        grades_qs = grades_qs.filter(is_active=(is_active_filter == 'true'))

    # 정렬 및 회원 수 계산 (원본)【:contentReference[oaicite:6]{index=6}】
    grades_qs = grades_qs.order_by('member_type', 'order', 'name').annotate(
        member_count=Count('member', filter=Q(member__is_deleted=False))
    )

    # 2) 페이지네이션 (원본)【:contentReference[oaicite:7]{index=7}】
    paginator = Paginator(grades_qs, 20)
    page = request.GET.get('page', 1)
    grades = paginator.get_page(page)

    # 3) 통계 데이터 (원본)【:contentReference[oaicite:8]{index=8}】
    stats = {
        'total': MemberGrade.objects.count(),
        'active': MemberGrade.objects.filter(is_active=True).count(),
        'b2c': MemberGrade.objects.filter(member_type='B2C').count(),
        'b2b': MemberGrade.objects.filter(member_type='B2B').count(),
    }

    # 4) rows(DTO) 구성: 템플릿은 반복 출력만 수행
    rows = []
    for g in grades:  # paginator Page는 iterable
        # (1) 등급 표시: 색상 점 + 아이콘 + 표시명/내부명(내부명이 다르면 보조로 노출)
        grade_display_html = format_html(
            '<div class="d-flex align-items-center">'
            '  <span class="grade-color mr-2" style="background-color: {};"></span>'
            '  <i class="{} grade-icon"></i>'
            '  <div><strong>{}</strong>{}</div>'
            '</div>',
            g.color_code or '#6c757d',
            g.icon_class or 'fas fa-user',
            escape(g.display_name or g.name),
            format_html('<br><small class="text-muted">{}</small>', escape(g.name))
            if (g.name and g.display_name and g.name != g.display_name) else ''
        )

        # (2) 액션 URL (사이드바와 일관되게 dashboard 네임스페이스 사용)
        update_url = reverse('dashboard:grade_update', args=[g.id])
        delete_url = reverse('dashboard:grade_delete', args=[g.id])

        rows.append({
            "grade_display": grade_display_html,           # 안전한 HTML
            "member_type": g.member_type,                  # 템플릿에서 뱃지 처리
            "order": g.order,
            "discount_rate": g.discount_rate,
            "point_rate": g.point_rate,
            "member_count": g.member_count,
            "is_active": g.is_active,
            "actions": {
                "update_url": update_url,
                "delete_url": delete_url,
                "name": g.display_name or g.name,         # confirm 메시지용
            },
        })

    # 5) 컨텍스트: 기존 'grades'도 유지(점진적 이전) + 새 columns/rows 제공
    context = {
        'grades': grades,  # 기존 템플릿 호환용
        'columns': GRADE_TABLE_COLUMNS,
        'rows': rows,
        'search': search,
        'member_type_filter': member_type_filter,
        'is_active_filter': is_active_filter,
        'stats': stats,
    }

    return render(request, 'dashboard/member/grade_list.html', context)


@staff_member_required
def grade_create(request):
    """등급 생성"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            display_name = request.POST.get('display_name', '').strip()
            member_type = request.POST.get('member_type')

            if not name or not member_type:
                messages.error(request, '등급명과 회원타입은 필수입니다.')
                return render(request, 'dashboard/member/grade_form.html', {
                    'form_data': request.POST
                })

            # 중복 체크 (원본)【:contentReference[oaicite:9]{index=9}】
            if MemberGrade.objects.filter(name=name, member_type=member_type).exists():
                messages.error(request, f'{member_type} 타입에 이미 {name} 등급이 존재합니다.')
                return render(request, 'dashboard/member/grade_form.html', {
                    'form_data': request.POST
                })

            # 등급 생성 (원본)【:contentReference[oaicite:10]{index=10}】
            grade = MemberGrade.objects.create(
                name=name,
                display_name=display_name or name,
                member_type=member_type,
                order=int(request.POST.get('order', 999)),
                discount_rate=float(request.POST.get('discount_rate', 0)),
                point_rate=float(request.POST.get('point_rate', 1.0)),
                auto_upgrade=request.POST.get('auto_upgrade') == 'on',
                min_order_count=int(request.POST.get('min_order_count') or 0) or None,
                min_total_amount=int(request.POST.get('min_total_amount') or 0) or None,
                min_period_amount=int(request.POST.get('min_period_amount') or 0) or None,
                is_default=request.POST.get('is_default') == 'on',
                color_code=request.POST.get('color_code', '#6c757d'),
                icon_class=request.POST.get('icon_class', 'fas fa-user'),
                is_active=request.POST.get('is_active', 'on') == 'on'
            )

            messages.success(request, f'{grade.display_name} 등급이 생성되었습니다.')
            # ✅ 리다이렉트 네임스페이스를 dashboard로 통일 (원본은 members)【원본 근거】
            return redirect('dashboard:grade_list')

        except Exception as e:
            messages.error(request, f'등급 생성 중 오류가 발생했습니다: {str(e)}')

    return render(request, 'dashboard/member/grade_form.html')


@staff_member_required
def grade_update(request, grade_id):
    """등급 수정"""
    grade = get_object_or_404(MemberGrade, id=grade_id)

    if request.method == 'POST':
        try:
            # 원본 필드 업데이트 로직 유지【:contentReference[oaicite:11]{index=11}】
            grade.display_name = request.POST.get('display_name', '').strip() or grade.name
            grade.order = int(request.POST.get('order', grade.order))
            grade.discount_rate = float(request.POST.get('discount_rate', grade.discount_rate))
            grade.point_rate = float(request.POST.get('point_rate', grade.point_rate))
            grade.auto_upgrade = request.POST.get('auto_upgrade') == 'on'

            grade.min_order_count = int(request.POST.get('min_order_count') or 0) or None
            grade.min_total_amount = int(request.POST.get('min_total_amount') or 0) or None
            grade.min_period_amount = int(request.POST.get('min_period_amount') or 0) or None

            grade.is_default = request.POST.get('is_default') == 'on'
            grade.color_code = request.POST.get('color_code', grade.color_code)
            grade.icon_class = request.POST.get('icon_class', grade.icon_class)
            grade.is_active = request.POST.get('is_active', 'on') == 'on'

            grade.save()

            messages.success(request, f'{grade.display_name} 등급이 수정되었습니다.')
            # ✅ 리다이렉트 네임스페이스를 dashboard로 통일 (원본은 members)【원본 근거】
            return redirect('dashboard:grade_list')

        except Exception as e:
            messages.error(request, f'등급 수정 중 오류가 발생했습니다: {str(e)}')

    context = {
        'grade': grade,
        'is_edit': True
    }
    return render(request, 'dashboard/member/grade_form.html', context)


@staff_member_required
@require_http_methods(["POST"])
def grade_delete(request, grade_id):
    """등급 삭제"""
    grade = get_object_or_404(MemberGrade, id=grade_id)

    try:
        member_count = grade.member_set.filter(is_deleted=False).count()

        if member_count > 0:
            return JsonResponse({
                'success': False,
                'message': f'해당 등급을 사용하는 회원이 {member_count}명 있어서 삭제할 수 없습니다.'
            })

        grade_name = grade.display_name
        grade.delete()

        return JsonResponse({
            'success': True,
            'message': f'{grade_name} 등급이 삭제되었습니다.'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'삭제 중 오류가 발생했습니다: {str(e)}'
        })


@staff_member_required
def member_grade_change(request):
    """회원 등급 일괄 변경"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            member_ids = data.get('member_ids', [])
            new_grade_id = data.get('grade_id')
            reason = data.get('reason', '관리자 일괄 변경')
            is_fixed = data.get('is_fixed', False)

            if not member_ids or not new_grade_id:
                return JsonResponse({
                    'success': False,
                    'message': '변경할 회원과 등급을 선택해주세요.'
                })

            new_grade = get_object_or_404(MemberGrade, id=new_grade_id)
            members = Member.objects.filter(id__in=member_ids, is_deleted=False)

            updated_count = 0

            with transaction.atomic():
                for member in members:
                    member.change_grade(
                        new_grade=new_grade,
                        reason='manual',
                        changed_by=request.user,
                        reason_detail=reason
                    )

                    if is_fixed:
                        member.fix_grade(reason=reason, fixed_by=request.user)

                    updated_count += 1

            return JsonResponse({
                'success': True,
                'message': f'{updated_count}명의 회원 등급이 변경되었습니다.'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'등급 변경 중 오류가 발생했습니다: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})


@staff_member_required
def grade_history(request, member_id):
    """회원별 등급 변경 이력"""
    member = get_object_or_404(Member, id=member_id)

    histories = MemberGradeHistory.objects.filter(member=member).order_by('-created_at')

    paginator = Paginator(histories, 10)
    page = request.GET.get('page', 1)
    histories_page = paginator.get_page(page)

    context = {
        'member': member,
        'histories': histories_page,
    }

    return render(request, 'dashboard/member/grade_history.html', context)
