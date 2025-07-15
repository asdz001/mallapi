import os, json, requests
from decimal import Decimal
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import transaction
from shop.models import RawProduct
from shop.models import RawProductOption  # 옵션 모델 존재 시
from utils.product_logger import get_product_logger

# ✅ 로거 생성
logger = get_product_logger("IT-B-01")

# 설정
SHOP_ID = "BASE BLU"
CONFIG = {
    "BASE BLU": {
        # "key": "61a61031e8107c472fc312f3-66013c37f598544a853a23fd:5d630d9844a6d0827d14247d6cafeec0", #테스트 키키
        'key': '61a61031e8107c472fc312f3-6791f518791ad1287012b863:b151b2e915b67e6bbafd22e230f959bb',
    }
}


API_BASE_URL = "https://api.csplatform.io"
#API_BASE_URL = "https://sandbox.csplatform.io:9950" #테스트 주소
EXPORT_DIR = Path("export") / SHOP_ID.upper().replace(" ", "")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_JSON = EXPORT_DIR / f"{SHOP_ID.lower().replace(' ', '_')}_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
CATEGORY_JSON = EXPORT_DIR / "categories.json"



def fetch_all_products(shop_id, page_size=250, max_threads=5):
    logger.info("📡 상품 수집 시작...")
    token = CONFIG[shop_id]["key"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 먼저 전체 상품 수량 확인
    params = {"_pageIndex": 0, "_pageSize": 1, "withQuantities": "true"}
    url = f"{API_BASE_URL}/shop/v1/items"
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    total_items = response.json().get("_metadata", {}).get("total_items", 0)
    total_pages = (total_items + page_size - 1) // page_size
    logger.info(f"📄 전체 상품 수: {total_items}개 / 총 페이지 수: {total_pages}페이지")

    def fetch_page(index):
        params = {
            "_pageIndex": index,
            "_pageSize": page_size,
            "withQuantities": "true"
        }
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            content = res.json().get("content", [])
            # 🔥 재고가 없는 상품은 제거
            filtered = [
                item for item in content
                if any(int(wh.get("qty", 0)) > 0 for wh in item.get("whs", []))
            ]
            return filtered
        except Exception as e:
            logger.error(f"❌ {index}페이지 수집 실패: {e}")
            return []

    from concurrent.futures import ThreadPoolExecutor, as_completed
    all_products = []

    with ThreadPoolExecutor(max_threads) as executor:
        futures = [executor.submit(fetch_page, i) for i in range(total_pages)]
        for future in as_completed(futures):
            all_products.extend(future.result())

    logger.info(f"✅ 재고 있는 상품 수집 완료: {len(all_products)}개")
    return all_products


# ✅ 카테고리 다운로드 및 매핑
def fetch_and_save_categories():
    logger.info("📂 카테고리 수집 시작...")

    token = CONFIG[SHOP_ID]["key"]
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_BASE_URL}/shop/v1/categories/tree"  # ✅ 트리형 API로 수정

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    categories = {}

    def traverse(node, path=""):
        if not isinstance(node, dict):
            logger.warning(f"⚠️ 잘못된 노드 형식: {node}")
            return

        current_path = f"{path} > {node['name']}" if path else node["name"]
        node_id = node.get("id", {}).get("$oid")
        if node_id:
            categories[node_id] = current_path

        for child in node.get("children", []):
            traverse(child, current_path)

    for root in data:
        traverse(root)

    with open(CATEGORY_JSON, "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ 카테고리 저장 완료: {CATEGORY_JSON}")
    return categories


# ✅ 전체 파이프라인 실행
@transaction.atomic
def run_full_baseblue_pipeline(limit=None):
    categories = fetch_and_save_categories()
    raw_products = fetch_all_products(SHOP_ID) 
    if limit:
        raw_products = raw_products[:limit]

    # 🔹 JSON 저장 추가
    EXPORT_JSON = EXPORT_DIR / f"{SHOP_ID.lower().replace(' ', '_')}_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(EXPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(raw_products, f, ensure_ascii=False, indent=2)
    logger.info(f"📁 원본 상품 JSON 저장 완료: {EXPORT_JSON}")

    product_list_f = {}

    # 🔹 1단계: 상품 그룹핑 + 옵션 정리
    for raw in raw_products:
        try:
            props = raw.get("props", {})
            if not props.get("brand") or not props.get("sku_parent"):
                continue

            brand = props.get("brand")
            sku = props.get("sku_parent")
            season = props.get("season")
            price_org = Decimal(str(raw.get("sale_price") or 0))
            price_retail = Decimal(str(raw.get("stock_price") or 0))
            price_supply = Decimal(str(raw.get("sale_price") or 0))
            key = f"{brand}|{sku}|{season}|{price_org}|{price_retail}|{price_supply}"

            size = props.get("size")
            barcode = props.get("barcode")
            wh_list = raw.get("whs", [])
            stock = sum(int(wh["qty"]) for wh in wh_list if int(wh["qty"]) > 0)
            if stock <= 0:
                continue

            price = Decimal(str(raw.get("sale_price") or 0))

            option = {
                "id": raw["item_id"]["$oid"],
                "name": size,
                "quantity": stock,
                "barcode": barcode,
                "price": price,
            }

            if key in product_list_f:
                product_list_f[key]["options"].append(option)
                product_list_f[key]["raws"].append(raw)
            else:
                product_list_f[key] = {
                    "brand": brand,
                    "sku": sku,
                    "season": season,
                    "price_org": price_org,
                    "price_retail": price_retail,
                    "price_supply": price_supply,
                    "options": [option],
                    "raws": [raw]
                }

        except Exception as e:
            logger.error(f"❌ 상품 파싱 실패: {e}")
            continue

    # 🔹 2단계: 상품 저장
    saved, skipped = 0, 0
    for key, item in product_list_f.items():
        try:
            options = item["options"]
            raw = item["raws"][0]  # 대표 상품 하나 사용
            props = raw.get("props", {})
            locs = raw.get("locs", {})
            imgs = raw.get("imgs", [])

            # 카테고리
            category_id = raw.get("cats", [{}])[0].get("$oid")
            category_name = categories.get(category_id, "")
            parts = category_name.split(" > ")
            category1 = parts[0] if len(parts) > 0 else ""
            category2 = parts[1] if len(parts) > 1 else ""

            # 이미지 최대 4장
            image_urls = [img["url"] for img in imgs if img.get("url")] + [None] * 4
            image_urls = image_urls[:4]

            product_data = {
                "retailer": "IT-B-01",
                "raw_brand_name": item["brand"],
                "product_name": f"{item['brand']} {locs['singles']['title']['en']} {item['sku']}",
                "gender": props.get("sex"),
                "category1": category1,
                "category2": category2,
                "season": item["season"],
                "sku": item["sku"],
                "color": locs.get("singles", {}).get("color", {}).get("en"),
                "origin": props.get("made_in"),
                "material": raw.get("composition", [{}])[0].get("material", {}).get("en"),
                "discount_rate": Decimal("0.00"),
                "price_org": item["price_org"],
                "price_retail": item["price_retail"],
                "price_supply": item["price_supply"],
                "image_url_1": image_urls[0],
                "image_url_2": image_urls[1],
                "image_url_3": image_urls[2],
                "image_url_4": image_urls[3],
                "status": "pending",
            }

            # 상품 저장
            product, _ = RawProduct.objects.update_or_create(
                external_product_id=options[0]["id"],  # 대표 옵션 ID 사용
                retailer=product_data["retailer"],
                defaults=product_data,
            )

            # 옵션 저장
            RawProductOption.objects.filter(product=product).delete()
            RawProductOption.objects.bulk_create([
                RawProductOption(
                    product=product,
                    option_name=o["name"],
                    external_option_id=o["id"],  # ✅ item_id로 저장
                    stock=o["quantity"],
                    price=o["price"]
                ) for o in options
            ])

            saved += 1

        except Exception as e:
            logger.error(f"❌ 저장 실패: {e}")
            skipped += 1





    # 🔹 오늘 수집된 상품 ID들만 추출
    if product_list_f:  # 상품이 수집된 경우에만 품절 처리
        collected_ids = set(
            option["id"] for item in product_list_f.values() for option in item["options"]
        )



        #품절 처리 수정
        RawProduct.objects.filter(
            retailer="IT-B-01",
            external_product_id__in=collected_ids,
            status="soldout"
        ).update(status="pending")  # 또는 "converted" 로 복원


        # 품절 처리
        RawProduct.objects.filter(
            retailer="IT-B-01"
        ).exclude(
            external_product_id__in=collected_ids
        ).update(status="soldout")
    else:
        logger.warning("❗ 상품이 하나도 수집되지 않았습니다. soldout 처리는 건너뜁니다.")

    logger.info(f"🏁 전체 완료: 등록 {saved}개 / 실패 {skipped}개")
    return saved