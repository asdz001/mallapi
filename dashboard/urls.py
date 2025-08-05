# dashboard/urls.py

from django.urls import path, include
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('products/', include('shop_product.urls')), # 상품 관련 URL 포함
    path('members/', include('members.urls')), # 회원 관리 앱 URL 포함

    path('settings/', include('mall_settings.urls')), # 쇼핑몰 설정 앱 URL 포함
]



