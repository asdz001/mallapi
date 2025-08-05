# mall_settings/views/operator_list.py

from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

@staff_member_required
def operator_list_view(request):
    users = User.objects.filter(is_staff=True).select_related('operatorprofile')
    return render(request, 'dashboard/settings/operator_list.html', {
        'users': users
    })