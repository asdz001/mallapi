from django.shortcuts import render
from shop.models import Product
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.translation import gettext_lazy as _  # 다국어 지원을 위한 import
from datetime import datetime, timedelta  # 🆕 날짜 처리를 위한 import
from django.utils import timezone  # 🆕 시간대 처리


def dashboard_home(request):
    """대시보드 홈페이지"""
    return render(request, 'dashboard/home.html')
