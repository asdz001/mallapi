# members/urls.py - 등급 선택 API URL 추가
# ------------------------------------------------------------
# 기존 URL 패턴에 등급 관련 API 추가
# ------------------------------------------------------------

from django.urls import path

# ✅ 기존 정상 구조: 모듈 단위 import
from members.views import member_list, member_add, deleted_member_list, grade_views 

# ✅ 신규 API 전용 모듈 (등급 선택 API 추가)
from members.views import member_detail  # member_detail.get_member_grades_api 추가

urlpatterns = [
    # =========================
    # ✅ 활성 회원 관리
    # =========================
    path('', member_list.member_list, name='member_list'),                 # 회원 목록
    path('add', member_add.member_add, name="member_add"),                 # 회원 추가

    # ✅ 회원 삭제 관련 (AJAX)
    path('delete/<int:member_id>', member_list.member_delete, name='member_delete'),              # 개별 삭제
    path('bulk-action', member_list.member_bulk_action, name='member_bulk_action'),               # 벌크 액션

    # =========================
    # 🆕 회원 상세/수정/활동 API (모달/탭용 AJAX) - 등급 관리 포함
    # =========================
    path('detail/<int:member_id>', member_detail.member_detail_api, name='member_detail_api'),    # 상세보기
    path('update/<int:member_id>', member_detail.member_update_api, name='member_update_api'),    # 정보 수정
    path('activity/<int:member_id>', member_detail.member_activity_api, name='member_activity_api'),  # 활동 로그

    # ✅ 등급 선택 옵션 API 추가
    path('grades/<str:member_type>', member_detail.get_member_grades_api, name='get_member_grades_api'),  # 회원타입별 등급 목록

    # =========================
    # 🗂️ 삭제된 회원 관리
    # =========================
    path('deleted', deleted_member_list.deleted_member_list, name='deleted_member_list'),  # 삭제 회원 목록
    path('deleted/restore/<int:member_id>', deleted_member_list.restore_member, name='restore_member'),  # 복구
    path('deleted/permanent-delete/<int:member_id>', deleted_member_list.permanent_delete_member, name='permanent_delete_member'),  # 완전 삭제

    # ✅ 삭제된 회원 벌크 작업 (AJAX)
    path('deleted/bulk-restore', deleted_member_list.bulk_restore_members, name='bulk_restore_members'),  # 벌크 복구
    path('deleted/bulk-permanent-delete', deleted_member_list.bulk_permanent_delete_members, name='bulk_permanent_delete_members'),  # 벌크 완전삭제

    # 🆕 등급 관리 URL 추가
    path('grade', grade_views.grade_list, name='grade_list'),
    path('grade/create', grade_views.grade_create, name='grade_create'),
    path('grade/<int:grade_id>/update', grade_views.grade_update, name='grade_update'),
    path('grade/<int:grade_id>/delete', grade_views.grade_delete, name='grade_delete'),
    path('grade/bulk-change', grade_views.member_grade_change, name='member_grade_change'),
    path('grade/history/<int:member_id>', grade_views.grade_history, name='grade_history'),

    # =========================
    # 📄 향후 구현 예정 (인터페이스만)
    # =========================
    # path('self-withdrawal', customer_self_withdrawal, name='customer_self_withdrawal'),  # 고객 자율 탈퇴
]