from django.core.management.base import BaseCommand
from pricing.models import Retailer
from shop.api.pipeline_runner import run_full_pipeline_by_retailer

class Command(BaseCommand):
    help = "엘레노라 상품 수집 + 등록 + 가공 전체 파이프라인 실행"

    def handle(self, *args, **kwargs):
        retailer_code = "IT-E-01"

        self.stdout.write(self.style.NOTICE(f"🚀 [엘레노라] 파이프라인 시작: 거래처 코드={retailer_code}"))

        try:
            fetch_count, register_count = run_full_pipeline_by_retailer(retailer_code)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ 파이프라인 실패: {e}"))
            return

        self.stdout.write(self.style.SUCCESS(f"✅ 완료: 수집 {fetch_count}개 / 등록 {register_count}개"))



