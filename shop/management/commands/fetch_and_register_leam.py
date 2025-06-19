# shop/management/commands/fetch_and_register_leam.py

from django.core.management.base import BaseCommand
from shop.api.pipeline_runner import run_full_pipeline_by_retailer

class Command(BaseCommand):
    help = "📦 리암 상품을 수집하고 등록합니다"

    def handle(self, *args, **kwargs):
        retailer_code = "IT-L-01"  # 리암 고유 코드
        print("📥 리암 상품 수집 + 등록 시작")
        fetch_count, register_count = run_full_pipeline_by_retailer(retailer_code)
        print(f"✅ 완료: 수집 {fetch_count}개 / 등록 {register_count}개")