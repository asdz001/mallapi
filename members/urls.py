from django.urls import path
from members.views import member_list

urlpatterns = [
    path('', member_list.member_list, name='member_list'),  # 회원 목록 페이지
]


