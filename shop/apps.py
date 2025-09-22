from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'
    verbose_name = "🛒 SHOP"

    def ready(self):
        # ✅ 시그널 등록 (앱 로딩 시 shop/signals.py 실행)
        import shop.signals