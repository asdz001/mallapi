from django.core.management.base import BaseCommand
from shop.api.atelier.convert_bini_products import convert_atelier_products
from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer
from pricing.models import Retailer
from django.utils import timezone


class Command(BaseCommand):
    help = "BINI 상품 자동 수집 및 등록"

    def handle(self, *args, **options):
        retailer_code = "IT-B-02"
        fetch_count = 0
        register_count = 0

        retailer = Retailer.objects.get(code=retailer_code)
        retailer.last_fetch_started_at = timezone.now()
        retailer.save()

        # ✅ [1/2] 수집 및 원본상품 등록
        print("🟡 [1/2] BINI 상품 수집 및 저장 시작")
        fetch_count = convert_atelier_products()

        # ✅ [2/2] 가공상품 등록
        print("🟡 [2/2] 가공상품 등록 시작")
        register_count = bulk_convert_or_update_products_by_retailer(retailer_code)

        # ✅ 결과 저장
        retailer.last_fetch_finished_at = timezone.now()
        retailer.last_register_finished_at = timezone.now()
        retailer.last_fetched_count = fetch_count or 0
        retailer.last_registered_count = register_count or 0
        try:
            retailer.save()
        except Exception as e:
            print(f"❌ Retailer 저장 실패: {e}")

        # ✅ 완료 메시지
        print(f"✅ BINI 전체 프로세스 완료 - 수집: {fetch_count}개 / 등록: {register_count}개")
        return f"수집: {fetch_count}개 / 등록: {register_count}개"
