# shop_product/urls.py

from django.urls import path
from shop_product.views import product_list, product_add, classification # views.list 모듈에서 불러오기


urlpatterns = [
    path('', product_list.product_list, name='product_list'),
    path('add', product_add.product_add, name='product_add'),
    path('classification/supplier', classification.supplier_list, name='supplier_list'),
    path('classification/category', classification.category_list, name='category_list'),
    path('classification/origin', classification.origin_list, name='origin_list'),
    path('classification/brand', classification.brand_list, name='brand_list'),


]