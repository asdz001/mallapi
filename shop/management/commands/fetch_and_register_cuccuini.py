import json
import os
import time
from django.core.management.base import BaseCommand
from shop.api.atelier.cuccuini.fetch_goods_list import fetch_goods_list_CUCCUINI
from shop.api.atelier.cuccuini.fetch_details import fetch_all_details
from shop.api.atelier.cuccuini.fetch_prices import fetch_all_prices
from shop.api.atelier.cuccuini.convert_cuccuini_products import convert_CUCCUINI_raw_products
from shop.api.atelier.cuccuini.fetch_brand_category import fetch_brand_and_category_CUCCUINI
from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer
from pricing.models import Retailer
from django.utils import timezone

class Command(BaseCommand):
    help = "CUCCUINI 상품 자동 수집 및 등록"

    def handle(self, *args, **options):
        retailer_code = "IT-C-02"
        fetch_count = 0
        register_count = 0

        retailer = Retailer.objects.get(code=retailer_code)
        retailer.last_fetch_started_at = timezone.now()
        retailer.save()

        # ✅ [0/6] 브랜드 및 카테고리 수집
        print("📦 [0/6] 브랜드 및 카테고리 수집 시작")
        fetch_brand_and_category_CUCCUINI()

        # ✅ [1/6] 상품 기본 정보 수집
        print("🟡 [1/6] 상품 수집 시작")
        goods_start = time.time()
        fetch_goods_list_CUCCUINI()
        wait_until_done_file_updated("export/CUCCUINI/CUCCUINI_goods.done", after_timestamp=goods_start)

        # ✅ [2/6] 상세 정보 수집
        print("🟡 [2/6] 상세 정보 수집 시작")
        detail_start = time.time()
        fetch_all_details()
        wait_until_done_file_updated("export/CUCCUINI/CUCCUINI_details.done", after_timestamp=detail_start)

        # ✅ [3/6] 가격 정보 수집
        print("🟡 [3/6] 가격 정보 수집 시작")
        price_start = time.time()
        fetch_all_prices()
        wait_until_done_file_updated("export/CUCCUINI/CUCCUINI_prices.done", after_timestamp=price_start)

        # ✅ [4/6] 상품 등록
        print("🟡 [4/6] 상품 등록 시작")
        fetch_count = convert_CUCCUINI_raw_products()

        # ✅ [5/6] 가공상품 등록
        print("🟡 [5/6] 가공상품 등록 시작")
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
        print(f"✅ CUCCUINI 전체 프로세스 완료 - 수집: {fetch_count}개 / 등록: {register_count}개")
        return f"수집: {fetch_count}개 / 등록: {register_count}개"


# ✅ `.done` 파일이 최신인지 확인
def wait_until_done_file_updated(path, after_timestamp, timeout=30):
    for i in range(timeout):
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            if mtime > after_timestamp:
                print(f"✅ {os.path.basename(path)} 완료 확인됨 (mtime: {mtime})")
                return
            else:
                print(f"⏳ {os.path.basename(path)}는 이전 작업의 흔적입니다 (mtime: {mtime})")
        else:
            print(f"⏳ {os.path.basename(path)} 생성 대기 중...")
        time.sleep(1)
    raise Exception(f"❌ 제한 시간 내 파일 업데이트 실패: {path}")
