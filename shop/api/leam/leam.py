import requests
import os
import json
from datetime import datetime
from typing import List, Dict
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from shop.models import RawProduct, RawProductOption, Retailer
from django.db import transaction
from django.utils.timezone import now

# ✅ 기본 설정값
RETAILER_CODE = "IT-L-01"
BASE_URL = "https://srv2.best-fashion.net"
TOKEN = "292ae87edb8e5f2a15dd489f5c10b4b9"
EXPORT_DIR = "export/leam"
IMAGE_SAVE_DIR = "media/leam"
IMAGE_BASE_URL = f"{BASE_URL}/img"

# ✅ 로컬 저장 경로 생성
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)

def fetch_all_products() -> List[Dict]:
    """리암 전체 상품 수집 및 JSON 저장"""
    print("📡 리암 전체 상품 수집 시작...")
    url = f"{BASE_URL}/ApiV3/token/{TOKEN}/callType/allStockGroup"
    try:
        response = requests.get(url)
        response.raise_for_status()
        products = response.json()
        product_list = products.get("products", [])

        # ✅ 항상 같은 이름으로 저장 (덮어쓰기)
        output_path = os.path.join(EXPORT_DIR, "leam_full_catalog.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        print(f"✅ 수집 완료: 총 {len(product_list)}개 상품 → {output_path}")
        return product_list
    except Exception as e:
        print("❌ 요청 실패:", e)
        return []

def convert_leam_to_raw_format(raw_data: List[Dict]) -> List[Dict]:
    """리암 수집 데이터를 RawProduct 형식으로 변환"""
    converted = []
    for item in raw_data:
        if not item.get("available_size"):
            continue

        style_code = item.get("style_code", "")
        color_code = item.get("color_code", "")

        product = {
            "retailer": RETAILER_CODE,
            "external_product_id": item.get("product_id", ""),
            "product_name": f"{item.get('brand', '')} {item.get('name', '')} {style_code} {color_code}".strip(),
            "raw_brand_name": item.get("brand", ""),
            "gender": item.get("department", ""),
            "category1": item.get("category", ""),
            "category2": item.get("subcategory", ""),
            "color": item.get("color", ""),
            "description": item.get("description", ""),
            "price_org": float(item.get("price", 0)),
            "price_retail": float(item.get("default_price", 0)),
            "discount_rate": item.get("sale", 0),
            "sku": f"{style_code} {color_code}".strip(),
            "season": item.get("season", ""),
            "material": item.get("composition", ""),
            "origin": item.get("madein", ""),
            "image_url_1": item.get("pic1", ""),
            "image_url_2": item.get("pic2", ""),
            "image_url_3": item.get("pic3", ""),
            "image_url_4": item.get("pic4", ""),
            "options": []
        }

        for opt in item["available_size"]:
            product["options"].append({
                "option_name": opt.get("size", "ONE"),
                "stock": int(opt.get("qty", 0)),
                "price": float(item.get("price", 0)),
                "external_option_id": opt.get("stock_id", "")
            })

        converted.append(product)
    return converted

def download_and_optimize_image(image_name: str, resize_width=1200, quality=80) -> str:
    """이미지 다운로드 및 최적화 후 저장 (파일명은 원본 유지)"""
    if not image_name:
        return ""

    save_path = os.path.join(IMAGE_SAVE_DIR, image_name)
    if os.path.exists(save_path):
        return save_path

    try:
        url = f"{IMAGE_BASE_URL}/{image_name}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))

        if image.width > resize_width:
            height = int(resize_width * image.height / image.width)
            image = image.resize((resize_width, height), Image.ANTIALIAS)

        image.save(save_path, optimize=True, quality=quality)
        print(f"🖼️ 이미지 저장 완료: {image_name}")
        return save_path
    except Exception as e:
        print(f"❌ 이미지 저장 실패: {image_name} - {e}")
        return ""

def save_images_for_products(products: List[Dict]):
    """신규 상품 이미지 병렬 다운로드 처리"""
    tasks = []

    for product in products:
        external_id = product["external_product_id"]

        # 이미 존재하는 상품이면 이미지 다운로드 생략
        if RawProduct.objects.filter(external_product_id=external_id, retailer=RETAILER_CODE).exists():
            continue

        for i in range(1, 5):
            image_name = product.get(f"image_url_{i}")
            if image_name:
                tasks.append(image_name)

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(download_and_optimize_image, tasks)


def register_raw_products_bulk(products: List[Dict]):
    """수집된 상품을 DB에 등록 및 갱신 (신규/수정/품절 처리 포함)"""
    retailer = Retailer.objects.get(code=RETAILER_CODE)
    existing_products = RawProduct.objects.filter(retailer=retailer)
    existing_map = {p.external_product_id: p for p in existing_products}

    incoming_ids = set(p["external_product_id"] for p in products)
    existing_ids = set(existing_map.keys())

    new_products = []
    update_products = []
    updated_options = []
    now_dt = now()

    for p in products:
        external_id = p["external_product_id"]
        if external_id in existing_map:
            obj = existing_map[external_id]
            obj.price_org = p["price_org"]
            obj.price_retail = p["price_retail"]
            obj.discount_rate = p["discount_rate"]
            obj.status = "pending"
            obj.updated_at = now_dt
            update_products.append(obj)

            RawProductOption.objects.filter(raw_product=obj).delete()
            updated_options.extend([
                RawProductOption(
                    raw_product=obj,
                    option_name=opt["option_name"],
                    stock=opt["stock"],
                    price=opt["price"],
                    external_option_id=opt["external_option_id"]
                ) for opt in p["options"]
            ])
        else:
            new_products.append(RawProduct(
                retailer=retailer,
                external_product_id=external_id,
                product_name=p["product_name"],
                raw_brand_name=p["raw_brand_name"],
                gender=p["gender"],
                category1=p["category1"],
                category2=p["category2"],
                color=p["color"],
                description=p["description"],
                price_org=p["price_org"],
                price_retail=p["price_retail"],
                discount_rate=p["discount_rate"],
                sku=p["sku"],
                season=p["season"],
                material=p["material"],
                origin=p["origin"],
                image_url_1=p["image_url_1"],
                image_url_2=p["image_url_2"],
                image_url_3=p["image_url_3"],
                image_url_4=p["image_url_4"],
                status="pending",
                created_at=now_dt,
                updated_at=now_dt
            ))

    # ✅ DB 저장 및 업데이트
    with transaction.atomic():
        if new_products:
            RawProduct.objects.bulk_create(new_products, batch_size=1000)

        if update_products:
            RawProduct.objects.bulk_update(update_products, [
                "price_org", "price_retail", "discount_rate", "status", "updated_at"
            ], batch_size=500)

        if updated_options:
            RawProductOption.objects.bulk_create(updated_options, batch_size=1000)

        # ✅ 누락된 상품은 품절 처리 (status = "soldout")
        missing_ids = existing_ids - incoming_ids
        RawProduct.objects.filter(
            retailer=retailer,
            external_product_id__in=missing_ids
        ).update(status="soldout", updated_at=now_dt)

    print(f"✅ 신규 등록: {len(new_products)}개, 수정: {len(update_products)}개, 품절 처리: {len(missing_ids)}개")



def main():
    raw_data = fetch_all_products()
    mapped = convert_leam_to_raw_format(raw_data)
    save_images_for_products(mapped)
    register_raw_products_bulk(mapped)
    return len(raw_data), len(mapped)