import json
import os
import time
from django.core.management.base import BaseCommand
from shop.api.atelier.minetti.fetch_goods_list import fetch_goods_list_MINETTI
from shop.api.atelier.minetti.fetch_details import fetch_all_details
from shop.api.atelier.minetti.fetch_prices import fetch_all_prices
from shop.api.atelier.minetti.fetch_brand_category import fetch_brand_and_category_MINETTI
from shop.api.atelier.minetti.convert_minetti_products import convert_MINETTI_raw_products
from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer



class Command(BaseCommand):
    help = "MINETTI 상품 자동 수집 및 등록"

    def handle(self, *args, **options):
        # ✅ [0/6] 브랜드 및 카테고리 수집
        print("📦 [0/6] 브랜드 및 카테고리 수집 시작")
        fetch_brand_and_category_MINETTI()
        
        # 상품기본정보 수집
        print("🟡 [1/6] 상품 수집 시작")
        fetch_goods_list_MINETTI()

        print("🔍 [2/6] 상품 수 확인 중...")
        wait_until_data_ready("export/MINETTI/MINETTI_goods.json", minimum_count=500)

        # 상품 디테일 정보 수집
        print("🟡 [3/6] 상세 정보 수집 시작")
        fetch_all_details()

        print("🔍 [4/6] 상세 정보 수 확인 중...")
        wait_until_data_ready("export/MINETTI/MINETTI_details.json", minimum_count=1000)

        # 가격 수집
        print("🟡 [5/6] 가격 정보 수집 시작")
        fetch_all_prices()

        print("🔍 [6/6] 수집 완료 파일 확인 중...")
        wait_until_done_files([
            "export/MINETTI/MINETTI_goods.done",
            "export/MINETTI/MINETTI_details.done",
            "export/MINETTI/MINETTI_prices.done"
        ])

        # 상품정보 취합
        print("🟡 상품 등록 시작")
        convert_MINETTI_raw_products()

        # 가공상품 등록
        print("🟡 가공상품 등록 시작")
        bulk_convert_or_update_products_by_retailer("IT-B-02")

        print("✅ MINETTI 전체 프로세스 완료")


# ⛳ 반드시 클래스 밖에 있어야 함
def wait_until_data_ready(path, minimum_count=1000, timeout=30):
    for i in range(timeout):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = len(data)
            if count >= minimum_count:
                print(f"✅ {os.path.basename(path)} 수 확인 완료: {count}개")
                return
            else:
                print(f"⏳ {os.path.basename(path)} 수 확인 중... 현재 {count}개")
        except Exception as e:
            print(f"⏳ 파일 확인 오류 ({path}): {e}")
        time.sleep(1)
    raise Exception(f"❌ 제한 시간 내 수 확인 실패: {path} (기준: {minimum_count}개)")


def wait_until_done_files(paths, timeout=30):
    for i in range(timeout):
        missing = [p for p in paths if not os.path.exists(p)]
        if not missing:
            print(f"✅ 모든 수집 완료 파일 확인 완료")
            return
        print(f"⏳ 아직 완료되지 않은 단계: {missing}")
        time.sleep(1)
    raise Exception(f"❌ 제한 시간 내 완료 표시 파일이 생성되지 않았습니다: {missing}")
