import datetime
from decimal import Decimal, InvalidOperation
from django.db import transaction
from shop.api.atelier.atelier_api import Atelier
from shop.models import RawProduct, RawProductOption

def safe_float(value):
    try:
        if value in (None, "null", "", "NaN"):
            return 0.0
        return float(str(value).replace(",", "."))
    except Exception:
        return 0.0

def safe_decimal(value):
    try:
        if value in (None, "", "null") or str(value).lower() == "nan":
            return Decimal("0.00")
        return Decimal(str(value).replace(",", "."))
    except InvalidOperation as e:
        print(f"❌ [safe_decimal 변환 오류] value='{value}' → {e}")
        return Decimal("0.00")

def extract_image_urls(picture_list):
    try:
        return [p.get("PictureUrl") for p in picture_list if isinstance(p, dict) and p.get("PictureUrl")][:4]
    except Exception:
        return []

def convert_bini_products(limit=None):
    print(f"📦 BINI 수집 시작: {datetime.datetime.now()}")
    atelier = Atelier("BINI")

    try:
        goods_list = atelier.get_goods_list()
        details_list = atelier.get_goods_details()
        prices_list = atelier.get_goods_prices()
        brand_list = atelier.get_brand_list()
        gender_list = atelier.get_gender_list()
        subcat_list = atelier.get_subcategory_list()
    except Exception as e:
        print(f"❌ [수집 실패] API 호출 중 오류 발생: {e}")
        return 0

    print(f"✅ 수집 완료 - 상품:{len(goods_list)} / 상세:{len(details_list)} / 가격:{len(prices_list)}")

    brand_dict = {b["ID"]: b["Name"] for b in brand_list}
    gender_dict = {g["ID"]: g["Name"] for g in gender_list}
    parent_name_map = {s["ParentID"]: s["ParentName"] for s in subcat_list if s.get("ParentID") and s.get("ParentName")}
    subcat_name_map = {s["ID"]: s["Name"] for s in subcat_list if s.get("ID") and s.get("Name")}

    detail_dict = {str(d.get("GoodsID")): d for d in details_list if d.get("GoodsID")}
    price_map = {
        (str(p.get("GoodsID")), p.get("Barcode"), p.get("Size", "").upper()): p for p in prices_list
    }

    success, fail, option_total = 0, 0, 0

    with transaction.atomic():
        for idx, good in enumerate(goods_list[:limit] if limit else goods_list):
            gid = str(good.get("ID"))
            instock = good.get("InStock", 0)
            try:
                instock = int(instock)
            except (TypeError, ValueError):
                instock = 0
            if instock <= 0:
                print(f"⛔ 재고 없음으로 스킵: ID={gid}")
                continue

            print(f"\n🔍 [{idx+1}] 상품 처리 중: ID={gid}")
            detail = detail_dict.get(gid)
            if not detail:
                print(f"⚠️ 상세정보 없음: {gid} → 공란 처리")

            sizes = [p for (gid_key, _, _), p in price_map.items() if gid_key == gid]
            if not sizes:
                print(f"⚠️ 프라이스 기준 옵션 없음: {gid}")
                fail += 1
                continue

            brand_name = brand_dict.get(str(good.get("BrandID")))
            gender = gender_dict.get(str(good.get("GenderID")))
            category1 = parent_name_map.get(str(good.get("ParentCategoryID")))
            category2 = subcat_name_map.get(str(good.get("CategoryID")))

            if not brand_name:
                print(f"⚠️ 브랜드 매핑 실패: {gid} / BrandID={good.get('BrandID')}")
                fail += 1
                continue
            if not category1 or not category2:
                print(f"⚠️ 카테고리 매핑 실패: {gid} / ParentID={good.get('ParentCategoryID')} / ID={good.get('CategoryID')}")
                fail += 1
                continue

            images = extract_image_urls(detail.get("Pictures", {}).get("Picture", []))
            image_url_1 = images[0] if len(images) > 0 else None
            image_url_2 = images[1] if len(images) > 1 else None
            image_url_3 = images[2] if len(images) > 2 else None
            image_url_4 = images[3] if len(images) > 3 else None

            price_org = max([
                safe_float((price_map.get((gid, s.get("Barcode"), s.get("Size", "").upper())) or {}).get("NetPrice"))
                for s in sizes
            ] or [0])

            first_key = (gid, sizes[0].get("Barcode"), sizes[0].get("Size", "").upper())
            price_data = price_map.get(first_key, {})
            price_retail = safe_decimal(price_data.get("BrandReferencePrice", "0"))
            discount = safe_decimal(price_data.get("Discount", "0"))

            try:
                product, _ = RawProduct.objects.update_or_create(
                    external_product_id=gid,
                    defaults={
                        "retailer": "IT-B-02",
                        "raw_brand_name": brand_name,
                        "product_name": f"{good.get('GoodsName')} {good.get('Model', '')} {good.get('Variant', '')}",
                        "gender": gender,
                        "category1": category1,
                        "category2": category2,
                        "season": good.get("Season"),
                        "sku": f"{good.get('Model', '')} {good.get('Variant', '')}",
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
                options = []
                for s in sizes:
                    barcode = s.get("Barcode")
                    size = s.get("Size", "").upper()
                    qty = int(s.get("Qty", "0"))
                    pkey = (gid, barcode, size)
                    price_data = price_map.get(pkey, {})
                    option_price_raw = price_data.get("SizeNetPrice") or price_data.get("NetPrice")
                    option_price = safe_float(option_price_raw)

                    options.append(RawProductOption(
                        product=product,
                        external_option_id=barcode,
                        option_name=size,
                        stock=qty,
                        price=Decimal(option_price)
                    ))
                    option_total += 1

                RawProductOption.objects.bulk_create(options)
                success += 1

            except Exception as e:
                fail += 1
                print(f"❌ 등록 실패: {gid} → {e}")

    print(f"\n✅ [완료] BINI 상품 등록 결과")
    print(f"    - 성공: {success}")
    print(f"    - 실패: {fail}")
    print(f"    - 옵션 수: {option_total}")
    print(f"📦 [END]   종료시간: {datetime.datetime.now()}")

    return success
