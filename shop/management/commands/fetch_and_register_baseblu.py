# shop/management/commands/fetch_and_register_baseblu.py

from django.core.management.base import BaseCommand
from shop.api.pipeline_runner import run_full_pipeline_by_retailer
from utils.product_logger import get_product_logger

class Command(BaseCommand):
    help = "🛍️ 바제블루 상품을 수집하고 등록합니다"

    def handle(self, *args, **kwargs):
        retailer_code = "IT-B-01"  # 바제블루 고유 코드
        logger = get_product_logger(retailer_code)
        logger.info("📥 바제블루 상품 수집 + 등록 시작")
        fetch_count, register_count = run_full_pipeline_by_retailer(retailer_code)
        logger.info(f"✅ 완료: 수집 {fetch_count}개 / 등록 {register_count}개")
