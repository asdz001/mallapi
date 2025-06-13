from django.core.management.base import BaseCommand
from shop.api.pipeline_runner import run_full_pipeline_by_retailer

class Command(BaseCommand):
    help = "📦 BINI 상품 자동 수집 및 등록"

    def handle(self, *args, **kwargs):
        retailer_code = "IT-B-02"  # 리테일 고유 코드
        print("📥 비니 상품 수집 + 등록 시작")

        fetch_count, register_count = run_full_pipeline_by_retailer(retailer_code)
        print(f"✅ 완료: 수집 {fetch_count}개 / 등록 {register_count}개")



