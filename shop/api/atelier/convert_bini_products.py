from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import transaction
from decimal import Decimal
from shop.models import RawProduct, RawProductOption
from shop.api.atelier.atelier_api import Atelier

# 설정값
MAX_WORKERS = 20
RETAILER = "BINI"
RETAILER_CODE = "IT-B-02"

# 안전하게 숫자로 바꾸는 함수 (오류 방지용)
def safe_float(value):
    try:
        if value in (None, "null", "", "NaN"):
            return 0.0
        return float(str(value).replace(",", "."))
    except Exception as e:
        print(f"❌ [가격 변환 오류] value='{value}' → {e}")
        return 0.0

def safe_decimal(value):
    try:
        if value in (None, "", "null") or str(value).lower() == "nan":
            return Decimal("0.00")
        return Decimal(str(value).replace(",", "."))
    except Exception as e:
        print(f"❌ [Decimal 변환 오류] value='{value}' → {e}")
        return Decimal("0.00")

# 1. 전체 상품 수집 함수 (재고 1개 이상만)
def fetch_goods_data():
    atelier = Atelier(RETAILER)

    print("📦 상품 기본 정보 수집 중...")
    goods_list = atelier.get_goods_list().get("GoodsList", {}).get("Good", [])
    print(f"✅ 전체 수집된 상품 수: {len(goods_list)}개")

    goods_ids = [
        item["ID"] for item in goods_list
        if item.get("ID") and int(item.get("InStock", 0)) > 0
    ]

    print(f"🟢 재고 있는 상품 수: {len(goods_ids)}개")

    print("📦 전체 상세 정보 및 가격 수집 중 (일감)...")
    detail_all = atelier.get_goods_detail_list().get("GoodsDetailList", {}).get("Good", [])
    price_all = atelier.get_goods_price_list().get("GoodsPriceList", {}).get("Price", [])

    detail_map = {d["ID"]: d for d in detail_all if d.get("ID")}
    price_map = {p["ID"]: p for p in price_all if p.get("ID")}

    results = []
    for gid in goods_ids:
        detail = detail_map.get(gid)
        price = price_map.get(gid)
        if detail and price:
            results.append({"ID": gid, "detail": detail, "price": price})

    print(f"🎯 최종 수집 성공: {len(results)}개")
    return results, {str(g["ID"]): g for g in goods_list if g.get("ID")}

# 2. 정제 및 저장 함수
def convert_atelier_products():
    atelier = Atelier(RETAILER)

    brand_map = {str(b.get("ID")): b.get("Name") for b in atelier.get_brand_list().get("BrandList", {}).get("Brand", [])}
    gender_map = {str(g.get("ID")): g.get("Name") for g in atelier.get_gender_list().get("GenderList", {}).get("Gender", [])}

    subcategory_items = atelier.get_subcategory_list().get("SubCategoryList", {}).get("SubCategory", [])


    category_map = {
        (str(c.get("CategoryID")), str(c.get("GenderID"))): (c.get("ParentName"), c.get("CategoryName"))
        for c in subcategory_items
        if c.get("CategoryID") and c.get("GenderID") and c.get("ParentName") and c.get("CategoryName")
    }
    print("🔍 category_map 키 예시 (최대 5개):", list(category_map.keys())[:5])

    data, goods_dict = fetch_goods_data()
    new_options = []

    with transaction.atomic():
        for item in data:
            gid = str(item["ID"])
            detail = item.get("detail")
            price_obj = item.get("price")
            goods = goods_dict.get(gid, {})

            if not detail or not price_obj:
                print(f"⚠️ 상세/가격 정보 없음: {gid}")
                continue

            sizes = detail.get("Stock", {}).get("Item", [])
            if not sizes:
                print(f"⚠️ 옵션 없음: {gid}")
                continue

            brand_id = str(goods.get("BrandID"))
            brand_name = brand_map.get(brand_id)
            if not brand_name:
                print(f"⚠️ 브랜드 매핑 실패: {gid} (BrandID: {brand_id})")
                print(f"💬 현재 브랜드맵 키 목록: {list(brand_map.keys())[:10]}")
                continue

            gender = gender_map.get(str(goods.get("GenderID")))
            category_id = str(goods.get("CategoryID"))
            gender_id = str(goods.get("GenderID"))
            category_key = (category_id, gender_id)

            category1, category2 = category_map.get(category_key, (None, None))

            if not category1 or not category2:
                print(f"⚠️ 카테고리 매핑 실패: {gid} (CategoryID: {category_id}, GenderID: {gender_id})")
                print(f"💬 category_key 존재 여부: {category_key in category_map}")
                print(f"💬 현재 category_map 전체 키 수: {len(category_map)}")
                continue

            pictures = detail.get("Pictures", {}).get("Picture", [])
            image_urls = [p.get("PictureUrl") for p in pictures if isinstance(p, dict) and p.get("PictureUrl")] [:4]
            image_url_1 = image_urls[0] if len(image_urls) > 0 else None
            image_url_2 = image_urls[1] if len(image_urls) > 1 else None
            image_url_3 = image_urls[2] if len(image_urls) > 2 else None
            image_url_4 = image_urls[3] if len(image_urls) > 3 else None

            price_org = max([
                safe_float((p or {}).get("NetPrice", "0"))
                for p in price_obj.get("Retailers", [])
                if p.get("Retailer", "").lower() == RETAILER.lower()
            ] or [0])

            first_price = next((p for p in price_obj.get("Retailers", [])
                                if p.get("Retailer", "").lower() == RETAILER.lower()), {})

            retail_raw = first_price.get("BrandReferencePrice", "0")
            price_retail = safe_decimal(retail_raw)
            discount_raw = first_price.get("Discount", "0")
            discount = safe_decimal(discount_raw)

            product, _ = RawProduct.objects.update_or_create(
                external_product_id=gid,
                defaults={
                    "retailer": RETAILER_CODE,
                    "raw_brand_name": brand_name,
                    "product_name": f"{goods.get('GoodsName', '')} {goods.get('Model', '')} {goods.get('Variant', '')}",
                    "gender": gender,
                    "category1": category1,
                    "category2": category2,
                    "season": goods.get("Season"),
                    "sku": f"{goods.get('Model', '')} {goods.get('Variant', '')}",
                    "color": detail.get("Color"),
                    "origin": detail.get("MadeIn"),
                    "material": detail.get("Composition"),
                    "discount_rate": discount,
                    "image_url_1": image_url_1,
                    "image_url_2": image_url_2,
                    "image_url_3": image_url_3,
                    "image_url_4": image_url_4,
                    "price_org": Decimal(price_org),
                    "price_retail": price_retail,
                    "status": "pending"
                }
            )

            product.options.all().delete()
            for s in sizes:
                barcode = s.get("Barcode")
                size = s.get("Size", "")
                qty = int(s.get("Qty", "0"))

                option_price_raw = next((r.get("SizeNetPrice") or r.get("NetPrice") for r in price_obj.get("Retailers", [])
                                         if r.get("Retailer", "").lower() == RETAILER.lower()), "0")
                option_price = safe_float(option_price_raw)

                new_options.append(RawProductOption(
                    product=product,
                    external_option_id=barcode,
                    option_name=size,
                    stock=qty,
                    price=Decimal(option_price)
                ))

        RawProductOption.objects.bulk_create(new_options)
        print(f"✅ 상품 등록 완료: 상품 {len(data)}개 / 옵션 {len(new_options)}개")

        fetch_count = len(data)
        return fetch_count

if __name__ == "__main__":
    fetch_count = convert_atelier_products()
    print(f"📦 수집 완료: {fetch_count}개")
