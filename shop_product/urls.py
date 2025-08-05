# shop_product/urls.py

from django.urls import path
from shop_product.views import product_list, product_add, classification # views.list 모듈에서 불러오기


urlpatterns = [
    path('', product_list.product_list, name='product_list'),
    path('add', product_add.product_add, name='product_add'),
    
    # 🔧 거래처 관리 URL 패턴
    path('classification/supplier', classification.supplier_list, name='supplier_list'),
    path('classification/supplier/create', classification.supplier_create, name='supplier_create'),
    path('classification/supplier/<int:supplier_id>/detail', classification.supplier_detail, name='supplier_detail'),
    path('classification/supplier/<int:supplier_id>/update', classification.supplier_update, name='supplier_update'),
    path('classification/supplier/<int:supplier_id>/delete', classification.supplier_delete, name='supplier_delete'),
    
    # 🔧 기타 분류 관리 (추후 구현)
    path('classification/category', classification.category_list, name='category_list'),
    path('classification/origin', classification.origin_list, name='origin_list'),
    path('classification/brand', classification.brand_list, name='brand_list'),
]