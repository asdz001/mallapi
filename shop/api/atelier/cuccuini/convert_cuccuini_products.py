from django.db import transaction
from shop.models import RawProduct, RawProductOption
import json
import os
from decimal import Decimal

def safe_float(value):
    try:
        print(f"🧪 변환 시도: {value}")  # ← 여기를 넣으세요!
        if value in (None, "null", ""):
            return 0.0
        return float(str(value).replace(",", "."))
    except Exception as e:
        print(f"❌ [가격 변환 오류] value='{value}' → {e}")
        return 0.0

def extract_image_url(pictures, no):
    try:
        return next(
            (p.get("PictureUrl") for p in pictures if isinstance(p, dict) and p.get("No") == str(no)),
            None
        )
    except Exception as e:
        print(f"❌ 이미지 추출 오류 (No={no}): {e}")
        return None

def convert_cuccuini_raw_products(limit=None, goods_override=None):
    RETAILER = "CUCCUINI"
    BASE_PATH = os.path.join("export", RETAILER)
    goods_path = os.path.join(BASE_PATH, "cuccuini_goods.json")
    details_path = os.path.join(BASE_PATH, "cuccuini_details.json")
    prices_path = os.path.join(BASE_PATH, "cuccuini_prices.json")
    brand_path = os.path.join(BASE_PATH, "cuccuini_brand_mapping.json")
    gender_path = os.path.join(BASE_PATH, "cuccuini_gender_mapping.json")
    category_path = os.path.join(BASE_PATH, "cuccuini_category_mapping.json")

    # ✅ 경로 정의가 먼저 되어야 이 아래에서 사용 가능
    if goods_override:
        goods = goods_override
    else:
        goods = json.load(open(goods_path, encoding="utf-8"))
        if limit:
            goods = goods[:limit]


    details_raw = json.load(open(details_path, encoding="utf-8"))
    prices = json.load(open(prices_path, encoding="utf-8"))
    brand_map = {str(b.get("ID")): b.get("Name") for b in json.load(open(brand_path, encoding="utf-8"))}
    gender_map = {str(g.get("ID")): g.get("Name") for g in json.load(open(gender_path, encoding="utf-8"))}
    cat_map = {(str(c.get("ID")), str(c.get("GenderID"))): (c.get("ParentName"), c.get("Name")) for c in json.load(open(category_path, encoding="utf-8"))}
    details = {str(d.get("ID")): d for d in details_raw}

    price_map = {
        (str(p.get("GoodsID")), p.get("Barcode"), p.get("Size", "").upper()): p for p in prices
    }

    if limit:
        goods = goods[:limit]

    new_options = []
    with transaction.atomic():
        for g in goods:
            gid = str(g.get("ID"))
            detail = details.get(gid)

            if not detail:
                print(f"⚠️ 상품 상세 정보 없음: {gid}")
                continue

            sizes = detail.get("Stock", {}).get("Item", [])
            if not sizes or not isinstance(sizes, list) or len(sizes) == 0:
                print(f"⚠️ 옵션 없음 또는 형식 오류: {gid}")
                continue

            brand_name = brand_map.get(str(g.get("BrandID")))
            if not brand_name:
                print(f"⚠️ 브랜드 매핑 실패: {gid}, BrandID: {g.get('BrandID')}")
                continue

            gender = gender_map.get(str(g.get("GenderID")))
            category1, category2 = cat_map.get((str(g.get("CategoryID")), str(g.get("GenderID"))), (None, None))
            if not category1 or not category2:
                print(f"⚠️ 카테고리 매핑 실패: {gid}")
                continue

            # 이미지 처리
            pictures = []
            try:
                pictures_field = detail.get("Pictures", None)
                if isinstance(pictures_field, dict):
                    pictures_data = pictures_field.get("Picture", [])
                    pictures = pictures_data if isinstance(pictures_data, list) else []
                elif isinstance(pictures_field, list):
                    pictures = pictures_field
                else:
                    pictures = []
            except Exception as e:
                print(f"❌ 이미지 파싱 오류 (상품 ID: {gid}): {e}")
                pictures = []

            image_urls = [p.get("PictureUrl") for p in pictures if isinstance(p, dict) and p.get("PictureUrl")][:4]
            image_url_1 = image_urls[0] if len(image_urls) > 0 else None
            image_url_2 = image_urls[1] if len(image_urls) > 1 else None
            image_url_3 = image_urls[2] if len(image_urls) > 2 else None
            image_url_4 = image_urls[3] if len(image_urls) > 3 else None


            print(f"🎯 가격 디버깅: {[price_map.get((gid, s.get('Barcode'), s.get('Size', '').upper())) for s in sizes]}")
            # 완전 방어적 처리
            price_org = max([
                safe_float(
                    (price_map.get((gid, s.get("Barcode"), s.get("Size", "").upper())) or {}).get("NetPrice", "0")
                )
                for s in sizes
            ] or [0])


            first_price_key = (gid, sizes[0].get("Barcode"), sizes[0].get("Size", "").upper())
            retail_raw = price_map.get(first_price_key, {}).get("BrandReferencePrice") or "0"
            price_retail = Decimal(str(retail_raw).replace(",", "."))

            product, _ = RawProduct.objects.update_or_create(
                external_product_id=gid,
                defaults={
                    "retailer": "IT-C-02",
                    "raw_brand_name": brand_name,
                    "product_name": f"{g.get('GoodsName')} {g.get('Model', '')} {g.get('Variant', '')}",
                    "gender": gender,
                    "category1": category1,
                    "category2": category2,
                    "season": g.get("Season"),
                    "sku": f"{g.get('Model', '')} {g.get('Variant', '')}",
                    "color": detail.get("Color"),
                    "origin": detail.get("MadeIn"),
                    "material": detail.get("Composition"),
                    "discount_rate": Decimal(price_map.get(first_price_key, {}).get("Discount", "0").replace(",", ".")),
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
                size = s.get("Size", "").upper()
                qty = int(s.get("Qty", "0"))
                price_data = price_map.get((gid, barcode, size), {})
                option_price_raw = price_data.get("SizeNetPrice") or price_data.get("NetPrice") or "0"
                option_price = safe_float(option_price_raw)

                new_options.append(RawProductOption(
                    product=product,
                    external_option_id=barcode,
                    option_name=size,
                    stock=qty,
                    price=Decimal(option_price)
                ))

        RawProductOption.objects.bulk_create(new_options)
        print(f"✅ CUCCUINI 상품 등록 완료: 상품 {len(goods)}개 / 옵션 {len(new_options)}개")


def convert_cuccuini_raw_products_by_id(target_id):
    RETAILER = "CUCCUINI"
    BASE_PATH = os.path.join("export", RETAILER)
    goods_path = os.path.join(BASE_PATH, "cuccuini_goods.json")
    goods = json.load(open(goods_path, encoding="utf-8"))
    target_goods = [g for g in goods if str(g.get("ID")) == str(target_id)]

    if not target_goods:
        print(f"❌ 상품 ID {target_id}에 해당하는 상품을 찾을 수 없습니다.")
        return

    convert_cuccuini_raw_products(limit=None, goods_override=target_goods)