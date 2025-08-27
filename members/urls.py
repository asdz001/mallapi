# members/urls.py
# ------------------------------------------------------------
# 회원 관리 URL 패턴
# - 기존 정상 동작 방식을 유지 (모듈 import → member_list.member_delete 형태)
# - 새 상세/수정/활동 API는 member_detail 모듈로 분리, URL만 추가
# - URL 끝 슬래시 제거 (프론트 호출부와 정확히 일치시켜 301/404 방지)
# ------------------------------------------------------------

from django.urls import path

# ✅ 기존 정상 구조: 모듈 단위 import
from members.views import member_list, member_add, deleted_member_list

# ✅ 신규 API 전용 모듈 (안에 스텁 함수 3개가 있어야 함)
from members.views import member_detail  # member_detail.member_detail_api 등으로 접근

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
    # 🆕 회원 상세/수정/활동 API (모달/탭용 AJAX)
    # - 스텁(View) 먼저 배치 → 서버 안정화 → 점진 구현
    # =========================
    path('detail/<int:member_id>', member_detail.member_detail_api, name='member_detail_api'),    # 상세보기
    path('update/<int:member_id>', member_detail.member_update_api, name='member_update_api'),    # 정보 수정
    path('activity/<int:member_id>', member_detail.member_activity_api, name='member_activity_api'),  # 활동 로그

    # =========================
    # 🗂️ 삭제된 회원 관리
    # =========================
    path('deleted', deleted_member_list.deleted_member_list, name='deleted_member_list'),  # 삭제 회원 목록
    path('deleted/restore/<int:member_id>', deleted_member_list.restore_member, name='restore_member'),  # 복구
    path('deleted/permanent-delete/<int:member_id>', deleted_member_list.permanent_delete_member, name='permanent_delete_member'),  # 완전 삭제

    # ✅ 삭제된 회원 벌크 작업 (AJAX)
    path('deleted/bulk-restore', deleted_member_list.bulk_restore_members, name='bulk_restore_members'),  # 벌크 복구
    path('deleted/bulk-permanent-delete', deleted_member_list.bulk_permanent_delete_members, name='bulk_permanent_delete_members'),  # 벌크 완전삭제

    # =========================
    # 📄 향후 구현 예정 (인터페이스만)
    # =========================
    # path('self-withdrawal', customer_self_withdrawal, name='customer_self_withdrawal'),  # 고객 자율 탈퇴
]
