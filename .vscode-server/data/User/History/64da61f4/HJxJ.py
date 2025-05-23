
from django.contrib import admin
from django.urls import path, include  # ★ include를 추가합니다.
from shop.views_admin import save_cart_option
from django.http import HttpResponse


def home(request):
    return HttpResponse("🎉 Django 서버가 정상 작동 중입니다!")


urlpatterns = [
    path('admin/api/save-cart-option/', save_cart_option),  # ✅ 반드시 여기에 직접 있어야 함
    path('admin/', admin.site.urls),
    path('shop/', include('shop.urls')),  # ★ shop 앱의 urls.py 연결
    path('', home),  # ← 이거 추가

]