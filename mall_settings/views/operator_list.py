# views/operator_list.py

from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

def get_operator_table_columns():
    """운영자 목록 컬럼 정의"""
    return [
        { 'field': 'username', 'header': '아이디', 'width': '120px', 'align': 'center', 'default': '-' },
        { 'field': 'first_name', 'header': '이름', 'width': '120px', 'align': 'center', 'default': '-' },
        { 'field': 'email', 'header': '이메일', 'width': '200px', 'align': 'center', 'default': '-' },
        { 'field': 'contact_number', 'header': '연락처', 'width': '120px', 'align': 'center', 'default': '-' },
        { 'field': 'allowed_retailers', 'header': '접근 거래처', 'width': '200px', 'align': 'center', 'default': '없음' },
        { 'field': 'alerts', 'header': '알림 설정', 'width': '150px', 'align': 'center', 'default': '없음' },
    ]

def get_operator_data():
    users = User.objects.filter(is_staff=True).select_related('operatorprofile')
    operator_data = []

    for user in users:
        profile = getattr(user, 'operatorprofile', None)
        operator_data.append({
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'email': user.email,
            'contact_number': profile.contact_number if profile else '',
            'allowed_retailers': [r.name for r in profile.allowed_retailers.all()] if profile else [],
            'alerts': format_alerts(profile),
        })
    return operator_data


def format_alerts(profile):
    if not profile:
        return ''
    alerts = []
    if profile.receive_order_alerts:
        alerts.append('📦 주문')
    if profile.receive_stock_alerts:
        alerts.append('📦 재고')
    return ' / '.join(alerts) if alerts else '없음'

@staff_member_required
def operator_list_view(request):
    columns = get_operator_table_columns()
    operators = get_operator_data()
    return render(request, 'dashboard/settings/operator_list.html', {
        'table_columns': columns,
        'operators': operators
    })


# ✅ 4단계: templatetags/operator_extras.py 생성 안내
# 설명:
# HTML에서 `{{ item|get_item:col.field }}` 처럼 dict 값을 추출할 수 있도록

# operator_extras.py 파일 생성 후 아래 코드 추가:
# from django import template
# register = template.Library()
#
# @register.filter
def get_item(obj, key):
    return obj.get(key, '')
