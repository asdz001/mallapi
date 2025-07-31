from django.shortcuts import render
from django.utils.translation import gettext_lazy as _  # 다국어 지원을 위한 import





def product_add(request):
    """상품 추가 페이지"""
    return render(request, 'dashboard/product_add.html')