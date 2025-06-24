import sys
import os
import django

# ✅ 정확히 프로젝트 루트 (mallapi/) 까지 경로 설정
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.append(BASE_DIR)

# ✅ settings 경로 그대로 유지 (mallapi/settings.py 구조임)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mallapi.settings")

# ✅ Django 초기화
django.setup()


from shop.api.atelier.atelier_api import Atelier

RETAILER = "CUCCUINI"
TARGET_ID = "31829772"  # 수집하고 싶은 상품 ID

def main():
    atelier = Atelier(RETAILER)

    print(f"🔍 상품 ID {TARGET_ID} 수집 시도 중...")

    # ✅ 1. 먼저 상품 리스트에서 해당 상품 존재 확인
    goods_list = atelier.get_goods_list().get("GoodsList", {}).get("Good", [])
    goods_dict = {str(g.get("ID")): g for g in goods_list if g.get("ID")}

    if TARGET_ID not in goods_dict:
        print(f"❌ 상품 ID {TARGET_ID}를 GoodList에서 찾을 수 없음.")
        return

    target_goods = goods_dict[TARGET_ID]
    print("✅ 상품 기본 정보 발견")
    print(f"상품명: {target_goods.get('GoodsName')} | 모델: {target_goods.get('Model')} | 재고: {target_goods.get('InStock')}")

    # ✅ 2. 이제 상세정보와 가격정보 수집
    detail_list = atelier.get_goods_detail_list().get("GoodsDetailList", {}).get("Good", [])
    price_list = atelier.get_goods_price_list().get("GoodsPriceList", {}).get("Price", [])

    detail_dict = {str(d.get("ID")): d for d in detail_list if d.get("ID")}
    price_dict = {str(p.get("ID")): p for p in price_list if p.get("ID")}

    detail = detail_dict.get(TARGET_ID)
    price = price_dict.get(TARGET_ID)

    if not detail:
        print("❌ 상세 정보 없음")
    else:
        print("✅ 상세 정보:")
        print(f"- 색상: {detail.get('Color')}")
        print(f"- 원산지: {detail.get('MadeIn')}")
        print(f"- 소재: {detail.get('Composition')}")
        sizes = detail.get("Stock", {}).get("Item", [])
        for s in sizes:
            print(f"  → 옵션: {s.get('Size')} / 바코드: {s.get('Barcode')} / 재고: {s.get('Qty')}")

    if not price:
        print("❌ 가격 정보 없음")
    else:
        print("✅ 가격 정보:")
        for r in price.get("Retailers", []):
            if r.get("Retailer", "").lower() == RETAILER.lower():
                print(f"  → 가격: {r.get('NetPrice')} | 브랜드가: {r.get('BrandReferencePrice')} | 할인율: {r.get('Discount')}")

if __name__ == "__main__":
    main()
