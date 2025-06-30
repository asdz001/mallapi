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
from django.conf import settings

RETAILER_CODE = "IT-L-01"
BASE_URL = "https://srv2.best-fashion.net"
TOKEN = "292ae87edb8e5f2a15dd489f5c10b4b9"

EXPORT_DIR = "export/leam"
IMAGE_SAVE_DIR = "media/leam"
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)

# 🔧 Leam API에서 이미지 경로 prefix를 받아오는 함수
def get_image_base_url() -> str:
    try:
        url = f"{BASE_URL}/ApiV3/token/{TOKEN}"
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        image_prefix = data.get("image_url", "").strip("/")

        # ✅ 수정된 부분: 'http'로 시작하면 그대로 사용
        if image_prefix.startswith("http"):
            return image_prefix
        return f"https://{image_prefix}"
    
    except Exception as e:
        print("❌ 이미지 base URL 요청 실패:", e)
        return "https://srv2.best-fashion.net/img"
    

# 🔧 전체 상품 목록을 수집하는 함수
def fetch_all_products() -> List[Dict]:
    print("📡 Leam 상품 수집 시작...")
    url = f"{BASE_URL}/ApiV3/token/{TOKEN}/callType/allStockGroup"
    try:
        res = requests.get(url)
        res.raise_for_status()
        products = res.json()
        product_list = products.get("products", [])

        with open(os.path.join(EXPORT_DIR, "leam_full_catalog.json"), "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        print(f"✅ 총 {len(product_list)}개 상품 수집 완료")
        return product_list
    except Exception as e:
        print("❌ 상품 수집 실패:", e)
        return []


def build_media_url(path: str) -> str:
    return f"{settings.MEDIA_URL.rstrip('/')}/{path.lstrip('/')}"



def convert_leam_to_raw_format(raw_data: List[Dict]) -> List[Dict]:
    converted = []
    for item in raw_data:
        if not item.get("available_size"):
            continue

        style_code = item.get("style_code", "")
        color_code = item.get("color_code", "")
        brand = item.get("brand", "").replace(" ", "")
        folder = f"{brand.upper()}/{style_code}_{color_code}"

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
            "image_url_1": build_media_url(f"leam/{folder}/{item.get('pic1')}") if item.get("pic1") else "",
            "image_url_2": build_media_url(f"leam/{folder}/{item.get('pic2')}") if item.get("pic2") else "",
            "image_url_3": build_media_url(f"leam/{folder}/{item.get('pic3')}") if item.get("pic3") else "",
            "image_url_4": build_media_url(f"leam/{folder}/{item.get('pic4')}") if item.get("pic4") else "",
            "image_folder": folder,
            "options": [
                {
                    "option_name": opt.get("size", "ONE"),
                    "stock": int(opt.get("qty", 0) or 0),
                    "price": float(item.get("price", 0)),  # ⚠ 여전히 상품 가격으로 통일됨
                    "external_option_id": opt.get("stock_id", "")
                }
                for opt in item["available_size"]
            ]
        }
        converted.append(product)
    return converted

# 🔧 이미지 다운로드 및 덮어쓰기
def download_and_optimize_image(image_name: str, base_url: str, folder_name: str, resize_width=1200, quality=80, force=False) -> str:
    if not image_name:
        return ""

    folder_path = os.path.join(IMAGE_SAVE_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    save_path = os.path.join(folder_path, image_name)

    # 파일이 존재하고 강제 다운로드가 아니라면 생략
    if os.path.exists(save_path) and not force:
        return save_path

    try:
        url = f"{base_url}/{image_name}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        image = Image.open(BytesIO(response.content))

        if image.width > resize_width:
            height = int(resize_width * image.height / image.width)
            image = image.resize((resize_width, height), Image.Resampling.LANCZOS)

        image.save(save_path, optimize=True, quality=quality)
        return save_path
    except Exception as e:
        print(f"❌ 이미지 저장 실패: {image_name} - {e}")
        return ""
    
# 🔧 이미지 수집 (기존 상품 제외 + 파일 존재해도 덮어쓰기)
def save_images_for_products(products: List[Dict]):
    base_url = get_image_base_url()
    tasks = []

    # ✅ DB에 이미 존재하는 상품 필터링
    existing_ids = set(
        RawProduct.objects.filter(
            retailer=RETAILER_CODE
        ).values_list("external_product_id", flat=True)
    )

    for product in products:
        ext_id = product["external_product_id"]

        # DB에 있으면 이미지 다운로드 생략
        if ext_id in existing_ids:
            continue

        # DB에는 없지만 파일이 있더라도 덮어쓰기 위해 무조건 다운로드
        folder_name = product.get("image_folder", "")
        for i in range(1, 5):
            image_path = product.get(f"image_url_{i}")
            if image_path:
                image_name = os.path.basename(image_path)  # 'NDcxMDgy.JPG' ← 요청용
                tasks.append((image_name, base_url, folder_name))  # folder_name은 저장용


    # 병렬 이미지 다운로드 실행 (덮어쓰기)
    with ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(lambda args: download_and_optimize_image(*args, force=True), tasks)

# 🔧 DB 저장 처리: 신규/수정/품절
def register_raw_products_bulk(products: List[Dict]):

    # 🔹 거래처 객체 조회 (등록 시 필요)
    retailer = Retailer.objects.get(code=RETAILER_CODE)
    # 🔹 수집한 상품 ID만 추출 (신규/기존 비교용)    
    incoming_ids = [p["external_product_id"] for p in products]
    # 🔹 1. 수집된 상품 ID 기준으로 기존 상품을 부분 조회 (업데이트 대상만 조회)
    existing_products = RawProduct.objects.filter(
        retailer=retailer,
        external_product_id__in=incoming_ids
    )
    existing_map = {p.external_product_id: p for p in existing_products}

    # 🔹 2. 전체 상품 ID만 가볍게 추출 (soldout 판별용, 메모리 절약)
    all_existing_ids = set(
        RawProduct.objects.filter(retailer=retailer)
        .values_list("external_product_id", flat=True)
    )

    # 🔹 신규 등록 / 수정 대상 상품 / 옵션 리스트
    new_products = []
    update_products = []
    updated_options = []
    new_options = []

    now_dt = now()  # timestamp 공통 적용

    for p in products:
        external_id = p["external_product_id"]

        if external_id in existing_map:
            # ✅ 기존 상품 → 필드 업데이트 및 옵션 갱신
            obj = existing_map[external_id]
            obj.price_org = p["price_org"]
            obj.price_retail = p["price_retail"]
            obj.discount_rate = p["discount_rate"]
            obj.status = "pending"
            obj.updated_at = now_dt
            update_products.append(obj)

            # 기존 옵션 삭제 후 새로 등록
            RawProductOption.objects.filter(product=obj).delete()
            for opt in p["options"]:
                updated_options.append(RawProductOption(
                    product=obj,
                    option_name=opt["option_name"],
                    stock=opt["stock"],
                    price=opt["price"],
                    external_option_id=opt["external_option_id"]
                ))
        else:
            new_obj = RawProduct(
                retailer=RETAILER_CODE,
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
            )
            new_products.append(new_obj)

                # ✅ 옵션 저장 추가
            for opt in p["options"]:
                new_options.append(RawProductOption(
                    product=new_obj,
                    option_name=opt["option_name"],
                    stock=opt["stock"],
                    price=opt["price"],
                    external_option_id=opt["external_option_id"]
                ))


    # 🔹 DB 저장 작업: 한 번에 일괄 등록/수정
    with transaction.atomic():
        if new_products:
            RawProduct.objects.bulk_create(new_products, batch_size=1000)
        if new_options:
            RawProductOption.objects.bulk_create(new_options, batch_size=1000)    
        if update_products:
            RawProduct.objects.bulk_update(update_products, [
                "price_org", "price_retail", "discount_rate", "status", "updated_at"
            ], batch_size=500)
        if updated_options:
            RawProductOption.objects.bulk_create(updated_options, batch_size=1000)

        # 🔹 수집되지 않은 기존 상품 ID만 추출 → soldout 처리
        missing_ids = all_existing_ids - set(incoming_ids)
        RawProduct.objects.filter(
            retailer=retailer,
            external_product_id__in=missing_ids
        ).update(status="soldout", updated_at=now_dt)

    print(f"✅ 신규: {len(new_products)}개 | 수정: {len(update_products)}개 | 품절: {len(missing_ids)}개")
    return len(new_products) + len(update_products)
    

def main():
    raw_data = fetch_all_products()
    mapped = convert_leam_to_raw_format(raw_data)
    save_images_for_products(mapped)
    saved_count = register_raw_products_bulk(mapped)
    return len(mapped), saved_count
