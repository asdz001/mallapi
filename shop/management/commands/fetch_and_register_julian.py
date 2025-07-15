# ✅ shop/management/commands/fetch_and_register_julian.py

from django.core.management.base import BaseCommand
from shop.api.pipeline_runner import run_full_pipeline_by_retailer
from utils.product_logger import get_product_logger

class Command(BaseCommand):
    help = "📦 줄리안 상품을 수집하고 저장하고 가공상품까지 전환합니다"

    def handle(self, *args, **kwargs):
        retailer_code = "IT-J-01"
        logger = get_product_logger(retailer_code)
        logger.info("📥 줄리안 상품 수집 및 가공상품 전환 시작")
        fetch_count, register_count = run_full_pipeline_by_retailer(retailer_code)
        logger.info(f"✅ 완료: 수집 {fetch_count}개 / 등록 {register_count}개")



