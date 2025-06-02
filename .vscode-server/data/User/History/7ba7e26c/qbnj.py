import datetime
from decimal import Decimal, InvalidOperation
from shop.api.atelier.atelier_api import Atelier
from shop.models import RawProduct, RawProductOption
from django.db import transaction

# 보조 함수들
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
    except InvalidOperation:
        return Decimal("0.00")

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

# 본 함수: 수집 + 병합 + 등록
def convert_cuccuini_products(limit=None):
    print(f"📦 CUCCUINI 수집 시작: {datetime.datetime.now()}")
    atelier = Atelier("CUCCUINI")

    # Step 1: 수집
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

    # Step 2: 매핑 딕셔너리
    brand_dict = {b["ID"]: b["Name"] for b in brand_list}
    gender_dict = {g["ID"]: g["Name"] for g in gender_list}

    subcat_dict = {}
    for s in subcat_list:
        try:
            key = f"{s['GenderID']}|{s['ParentID']}|{s['ID']}"
            subcat_dict[key] = s["Name"]
        except KeyError as e:
            print(f"⚠️ [서브카테고리 매핑 실패] 항목: {s} → {e}")

    detail_dict = {str(d.get("GoodsID")): d for d in details_list if d.get("GoodsID")}
    price_map = {
        (str(p.get("GoodsID")), p.get("Barcode"), p.get("Size", "").upper()): p for p in prices_list
    }

    success, fail, option_total = 0, 0, 0

    with transaction.atomic():
        for good in goods_list[:limit] if limit else goods_list:
            gid = str(good.get("ID"))

            # ✅ InStock이 0 이하인 경우 무시
            instock = good.get("InStock", 0)
            try:
                 instock = int(instock)
            except (TypeError, ValueError):
                 instock = 0
            if instock <= 0:
                print(f"⛔ 재고 없음으로 스킵: ID={gid}")
                continue


            detail = detail_dict.get(gid)
            if not detail:
                continue

            sizes = detail.get("Stock", {}).get("Item", [])
            if not sizes:
                continue

            brand_name = brand_dict.get(str(good.get("BrandID")))
            gender = gender_dict.get(str(good.get("GenderID")))
            key = f"{good.get('GenderID')}|{good.get('ParentCategoryID')}|{good.get('SubCategoryID')}"
            category = subcat_dict.get(key)
            if not (brand_name and category):
                continue

            category1 = category.split(">")[0].strip()
            category2 = category.split(">")[-1].strip()

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
                        "retailer": "IT-C-02",
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

    print(f"🎉 등록 완료: 상품 {success}개 / 실패 {fail}개 / 옵션 {option_total}개")


    return success