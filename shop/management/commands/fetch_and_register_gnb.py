# shop/management/commands/fetch_and_register_gnb.py

from django.core.management.base import BaseCommand
from shop.models import RawProduct
from shop.api.gnb import gnb
from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer

RETAILER_CODE = "IT-G-01"

class Command(BaseCommand):
    help = "GNB 상품 수집 및 가공상품 등록 자동화"

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("🛍️  GNB 상품 수집 및 등록 시작")
        self.stdout.write("=" * 60)

        try:
            # ✅ 수집 + 원본 등록까지 수행
            fetch_count = gnb.main()  # gnb.py의 main 함수는 수집 및 등록 처리


            # ✅ 등록된 가공상품 수량 확인
            register_count = RawProduct.objects.filter(retailer=RETAILER_CODE, status="converted").count()
            
            # ✅ 가공상품 등록
            bulk_convert_or_update_products_by_retailer(RETAILER_CODE)

            self.stdout.write(f"\n📦 수집된 상품 수: {fetch_count}")
            self.stdout.write(f"🛠️  등록된 가공상품 수: {register_count}")
            self.stdout.write("✅ 작업 완료")

        except Exception as e:
            self.stderr.write(f"❌ 오류 발생: {e}")
