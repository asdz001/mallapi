from django.core.management.base import BaseCommand
from shop.api.atelier.cuccuini.fetch_goods_list import fetch_cuccuini_goods_list
from shop.api.atelier.cuccuini.fetch_details import fetch_cuccuini_details
from shop.api.atelier.cuccuini.fetch_prices import fetch_cuccuini_prices
from shop.api.atelier.cuccuini.convert_cuccuini_products import convert_cuccuini_raw_products

class Command(BaseCommand):
    help = "CUCCUINI 상품 자동 수집 및 등록"

    def handle(self, *args, **options):
        print("🟡 CUCCUINI 수집 시작")
        fetch_cuccuini_goods_list()
        fetch_cuccuini_details()
        fetch_cuccuini_prices()
        print("🟡 CUCCUINI 등록 시작")
        convert_cuccuini_raw_products()
        print("✅ CUCCUINI 전체 완료")
