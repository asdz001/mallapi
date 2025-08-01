# dashboard/views/classification.py

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required

# 🔹 거래처 목록 페이지
@staff_member_required
def supplier_list(request):
    return render(request, 'dashboard/classification/classification_supplier.html')

# 🔹 카테고리 목록 페이지
@staff_member_required
def category_list(request):
    return render(request, 'dashboard/classification/classification_category.html')

# 🔹 원산지 목록 페이지
@staff_member_required
def origin_list(request):
    return render(request, 'dashboard/classification/classification_origin.html')

# 🔹 브랜드 목록 페이지
@staff_member_required
def brand_list(request):
    return render(request, 'dashboard/classification/classification_brand.html')