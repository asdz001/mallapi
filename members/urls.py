# members/urls.py

from django.urls import path
from members.views import member_list, member_add, deleted_member_list

urlpatterns = [
    # ✅ 활성 회원 관리 (슬래시 제거로 사이드바 CSS 문제 해결)
    path('', member_list.member_list, name='member_list'),  # 회원 목록 페이지
    path('add', member_add.member_add, name="member_add"),  # 회원 추가
    
    # ✅ 회원 삭제 관련 (AJAX)
    path('delete/<int:member_id>', member_list.member_delete, name='member_delete'),  # 개별 삭제
    path('bulk-action', member_list.member_bulk_action, name='member_bulk_action'),  # 벌크 액션
    
    # ✅ 삭제된 회원 관리
    path('deleted', deleted_member_list.deleted_member_list, name='deleted_member_list'),  # 삭제 회원 목록
    path('deleted/restore/<int:member_id>', deleted_member_list.restore_member, name='restore_member'),  # 회원 복구
    path('deleted/permanent-delete/<int:member_id>', deleted_member_list.permanent_delete_member, name='permanent_delete_member'),  # 완전 삭제
    
    # ✅ 삭제된 회원 벌크 작업 (AJAX)
    path('deleted/bulk-restore', deleted_member_list.bulk_restore_members, name='bulk_restore_members'),  # 벌크 복구
    path('deleted/bulk-permanent-delete', deleted_member_list.bulk_permanent_delete_members, name='bulk_permanent_delete_members'),  # 벌크 완전삭제
    
    # ✅ 향후 구현 예정 (인터페이스만 준비)
    # path('self-withdrawal', customer_self_withdrawal, name='customer_self_withdrawal'),  # 고객 자율 탈퇴
]