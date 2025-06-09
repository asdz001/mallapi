
from django.contrib import admin
from django.urls import path, include  # ★ include를 추가합니다.
from shop.views_admin import save_cart_option
from django.http import HttpResponse
from django.conf.urls.i18n import i18n_patterns


def home(request):
    return HttpResponse("🎉 Django 서버가 정상 작동 중입니다!")


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),  # ✅ 필수: 언어 변경용 경로
    path('admin/api/save-cart-option/', save_cart_option),  # ✅ 반드시 여기에 직접 있어야 함
    path('admin/', admin.site.urls),
    path('shop/', include('shop.urls')),  # ★ shop 앱의 urls.py 연결
    path('', home),  # ← 이거 추가

]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),  # 관리자 경로 다국어 처리
)