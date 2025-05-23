from django.core.management.base import BaseCommand
from shop.services.product.latti import fetch_latti_raw_products_optimized
from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer

class Command(BaseCommand):
    help = "📦 라띠 상품을 수집하고 등록합니다"

    def handle(self, *args, **kwargs):
        retailer_code = "IT-R-01"  # 라띠 고유 코드
        print("📥 라띠 상품 수집 시작~")
        fetch_latti_raw_products_optimized()
        print("🛠️ 원본 → 가공상품 전환 시작~")
        bulk_convert_or_update_products_by_retailer(retailer_code)
        print("✅ 작업 완료~")
