# leam_test_1.py

import os
import sys
import django

# ✅ mallapi.settings 를 찾을 수 있게 mallapi 폴더의 상위 경로를 sys.path에 추가
# 현재 파일 경로: shop/api/leam/leam_test_1.py
# 목표: sys.path에 C:\Users\USER\mallapi 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# ✅ Django 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mallapi.settings")
django.setup()

# ✅ 함수 임포트
from shop.api.leam.leam import (
    fetch_all_products,
    convert_leam_to_raw_format,
    save_images_for_products,
    register_raw_products_bulk
)

def run_leam_top_15_test():
    print("🚀 Leam 상위 100개 상품 테스트 시작")

    raw_data = fetch_all_products()
    if not raw_data:
        print("❌ 상품 수집 실패 또는 데이터 없음")
        return

    mapped = convert_leam_to_raw_format(raw_data)
    sample = mapped[:20]
    print(f"📦 테스트 대상 상품 수: {len(sample)}개")

    save_images_for_products(sample)
    register_raw_products_bulk(sample)

    print("✅ Leam 테스트 완료: 100개 상품 처리")

if __name__ == "__main__":
    run_leam_top_15_test()
