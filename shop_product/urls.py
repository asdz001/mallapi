# shop_product/urls.py

from django.urls import path
from shop_product.views import product_list, product_add # views.list 모듈에서 불러오기


urlpatterns = [
    path('', product_list.product_list, name='product_list'),
    path('add', product_add.product_add, name='product_add'),
]