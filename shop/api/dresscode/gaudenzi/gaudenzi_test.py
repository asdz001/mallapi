# ✅ 독립 실행 가능한 가우덴찌 수집 스크립트 (common.py 의존 제거)
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

def call_dresscode_api(full_url: str, headers: dict, params: dict = None) -> dict:
    print(f"📡 요청 URL: {full_url}")
    print(f"🔍 파라미터: {params}")
    response = requests.get(full_url, headers=headers, params=params)
    print(f"🔄 상태코드: {response.status_code}")
    if response.status_code != 200:
        print(f"❌ 요청 실패: {response.status_code} - {response.text}")
        return {}
    return response.json()

def fetch_limited_products(from_datetime: str, limit: int = 50):
    """
    드레스코드 API에서 상품 수집 (최대 limit개만)
    """
    url = f"{BASE_URL}/channels/v2/api/feeds/en/clients/{CLIENT}/products"
    headers = {
        "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
        "client": CLIENT,
        "Accept": "application/json"
    }
    params = {
        "channelKey": CHANNEL_KEY,
        "from": from_datetime
    }

    data = call_dresscode_api(url, headers, params)
    products = data.get("data", []) if isinstance(data, dict) else []

    print(f"✅ 총 수집된 상품 수: {len(products)} → 상위 {limit}개만 저장")
    if not products:
        return

    convert_gaudenzi_products(products[:limit])

def convert_gaudenzi_products(products: list):
    """
    수집된 상품을 RawProduct와 RawProductOption으로 저장 (bulk 방식)
    """
    raw_product_list = []
    raw_option_list = []

    for item in products:
        external_id = item.get("productID")
        brand = item.get("brand") or ""
        name = item.get("name") or ""
        sku = item.get("sku") or ""
        season = item.get("season") or ""
        genre = item.get("genre") or ""
        type_ = item.get("type") or ""
        category = item.get("category") or ""
        color = item.get("color") or ""
        material = item.get("composition") or ""
        origin = item.get("madeIn") or ""
        price_org = item.get("wholesalePrice") or 0
        price_supply = item.get("price") or 0
        price_retail = item.get("retailPrice") or 0
        images = item.get("photos", [])
        image_url_1 = images[0] if len(images) > 0 else None
        image_url_2 = images[1] if len(images) > 1 else None
        image_url_3 = images[2] if len(images) > 2 else None
        image_url_4 = images[3] if len(images) > 3 else None
        created_at = item.get("productLastUpdated") or datetime.now().isoformat()

        product = RawProduct(
            retailer="IT-G-03",
            external_product_id=external_id,
            product_name=f"{brand} {name} {sku}",
            raw_brand_name=brand,
            season=season,
            gender=genre,
            category1=type_,
            category2=category,
            color=color,
            material=material,
            origin=origin,
            price_org=price_org,
            price_supply=price_supply,
            price_retail=price_retail,
            sku=sku,
            image_url_1=image_url_1,
            image_url_2=image_url_2,
            image_url_3=image_url_3,
            image_url_4=image_url_4,
            created_at=created_at,
        )
        raw_product_list.append(product)

    with transaction.atomic():
        RawProduct.objects.bulk_create(raw_product_list, batch_size=1000)

    raw_product_map = {
        p.external_product_id: p
        for p in RawProduct.objects.filter(external_product_id__in=[rp.external_product_id for rp in raw_product_list])
    }

    for item in products:
        external_id = item.get("productID")
        sizes = item.get("sizes", [])

        for opt in sizes:
            size = opt.get("size") or "ONE"
            stock = opt.get("stock") or 0
            barcode = opt.get("gtin") or None
            price = opt.get("price") or 0

            if external_id not in raw_product_map:
                continue

            option = RawProductOption(
                product=raw_product_map[external_id],
                option_name=size,
                stock=int(stock),
                price=price,
                external_option_id=barcode
            )
            raw_option_list.append(option)

    with transaction.atomic():
        RawProductOption.objects.bulk_create(raw_option_list, batch_size=1000)

    print(f"📦 상품 저장 완료: {len(raw_product_list)}개 / 옵션: {len(raw_option_list)}개")


if __name__ == "__main__":
    from_datetime = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z")
    fetch_limited_products(from_datetime, limit=50)
