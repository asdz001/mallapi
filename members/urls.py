#members/urls.py

from django.urls import path
from members.views import member_list , member_add

urlpatterns = [
    path('', member_list.member_list, name='member_list'),  # 회원 목록 페이지
    path('add', member_add.member_add, name="member_add"),
]


