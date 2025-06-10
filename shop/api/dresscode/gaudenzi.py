
import sys
import os
import django
import requests
from datetime import datetime, timedelta, timezone
from django.db import transaction

# Django 환경 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mallapi.settings")
django.setup()

from shop.models import RawProduct, RawProductOption

# 📌 설정값
BASE_URL = "https://api.dresscode.cloud"
CLIENT = "gaudenzi"
CHANNEL_KEY = "33a2aaeb-7ef2-44c5-bb66-0d3a84e9869f"
SUBSCRIPTION_KEY = "8da6e776b61e4a56a2b2bed51c8199ea"

RETAILER_CODE = "IT-G-03"



def call_dresscode_api(full_url: str, headers: dict, params: dict = None) -> dict:
    try:
        print(f"\n📡 요청 URL: {full_url}")
        print(f"🔍 파라미터: {params}")
        response = requests.get(full_url, headers=headers, params=params, timeout=15)
        print(f"🔄 상태코드: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ 요청 실패: {response.status_code} - {response.text}")
            return {}
        return response.json()
    except Exception as e:
        print(f"🚨 API 요청 예외 발생: {e}")
        return {}



def fetch_products(from_datetime: str):
    print(f"📡 요청 → from: {from_datetime}")
    url = f"{BASE_URL}/channels/v2/api/feeds/en/clients/{CLIENT}/products"
    headers = {
        "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
        "client": CLIENT,
        "Accept": "application/json"
    }
    params = {"channelKey": CHANNEL_KEY, "from": from_datetime}

    data = call_dresscode_api(url, headers, params)
    products = data.get("data", []) if isinstance(data, dict) else []

    print(f"✅ 총 수집된 상품 수: {len(products)}")
    if not products:
        return {"collected_count": 0, "registered_count": 0}

    return convert_gaudenzi_products(products)

def convert_gaudenzi_products(products: list):
    external_ids = [p.get("productID") for p in products if p.get("productID")]
    existing_products = {
        p.external_product_id: p
        for p in RawProduct.objects.filter(external_product_id__in=external_ids)
    }

    to_create, to_update = [], []
    for item in products:
        external_id = item.get("productID")
        if not external_id:
            continue

        brand = item.get("brand") or ""
        name = item.get("name") or ""
        sku = item.get("sku") or ""
        season = item.get("season") or ""
        genre = item.get("genre") or ""
        type_ = item.get("type") or ""
        category = item.get("category") or ""
        material = item.get("composition") or ""
        origin = item.get("madeIn") or ""
        price_org = item.get("wholesalePrice") or 0
        price_supply = item.get("price") or 0
        price_retail = item.get("retailPrice") or 0
        images = item.get("photos", [])
        created_at = item.get("productLastUpdated") or datetime.now().isoformat()

        common_fields = {
            "product_name": f"{brand} {name} {sku}",
            "raw_brand_name": brand,
            "season": season,
            "gender": genre,
            "category1": type_,
            "category2": category,
            "material": material,
            "origin": origin,
            "price_org": price_org,
            "price_supply": price_supply,
            "price_retail": price_retail,
            "sku": sku,
            "image_url_1": images[0] if len(images) > 0 else None,
            "image_url_2": images[1] if len(images) > 1 else None,
            "image_url_3": images[2] if len(images) > 2 else None,
            "image_url_4": images[3] if len(images) > 3 else None,
            "created_at": created_at,
        }

        if external_id in existing_products:
            product = existing_products[external_id]
            for k, v in common_fields.items():
                setattr(product, k, v)
            to_update.append(product)
        else:
            to_create.append(RawProduct(retailer=RETAILER_CODE, external_product_id=external_id, **common_fields))

    with transaction.atomic():
        if to_create:
            RawProduct.objects.bulk_create(to_create, batch_size=1000)
        if to_update:
            RawProduct.objects.bulk_update(to_update, list(common_fields.keys()), batch_size=1000)

    all_products = RawProduct.objects.filter(external_product_id__in=external_ids)
    product_map = {p.external_product_id: p for p in all_products}
    existing_options = {
        opt.external_option_id: opt
        for opt in RawProductOption.objects.filter(product__in=all_products)
        if opt.external_option_id
    }

    to_create_opt, to_update_opt = [], []
    for item in products:
        external_id = item.get("productID")
        sizes = item.get("sizes", [])
        for opt in sizes:
            barcode = opt.get("gtin")
            if not barcode:
                continue
            size = opt.get("size") or "ONE"
            stock = int(opt.get("stock") or 0)
            price = opt.get("price") or 0

            if barcode in existing_options:
                obj = existing_options[barcode]
                if obj.stock != stock or obj.price != price:
                    obj.stock = stock
                    obj.price = price
                    to_update_opt.append(obj)
            elif external_id in product_map:
                to_create_opt.append(RawProductOption(
                    product=product_map[external_id],
                    option_name=size,
                    stock=stock,
                    price=price,
                    external_option_id=barcode
                ))

    with transaction.atomic():
        if to_create_opt:
            RawProductOption.objects.bulk_create(to_create_opt, batch_size=1000)
        if to_update_opt:
            RawProductOption.objects.bulk_update(to_update_opt, ["stock", "price"], batch_size=1000)

    print(f"📦 상품 저장 완료: 신규 {len(to_create)}개 / 수정 {len(to_update)}개")
    print(f"📦 옵션 저장 완료: 신규 {len(to_create_opt)}개 / 수정 {len(to_update_opt)}개")

    return {
        "collected_count": len(products),
        "registered_count": len(to_create) + len(to_update)
    }

def fetch_daily():
    print("⏱ [일일 수집 모드] from=어제")
    from_datetime = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z")
    return fetch_products(from_datetime)

def fetch_full_history(start_str="2024-01-01"):
    print("🗂 [전체 수집 모드] 시작일 →", start_str)
    start_date = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)

    total_collected = 0
    total_registered = 0

    while start_date < end_date:
        from_str = start_date.strftime("%Y-%m-%dT00:00:00.000Z")
        result = fetch_products(from_str)
        total_collected += result["collected_count"]
        total_registered += result["registered_count"]
        start_date += timedelta(days=7)

    return {
        "collected_count": total_collected,
        "registered_count": total_registered
    }

if __name__ == "__main__":
    if "--full" in sys.argv:
        fetch_full_history()
    else:
        fetch_daily()
