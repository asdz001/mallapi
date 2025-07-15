import os
import re
import requests
import json
import pandas as pd
import io
from django.db import transaction
from shop.models import RawProduct, RawProductOption
from utils.product_logger import get_product_logger


# ✅ 로거 생성
logger = get_product_logger("IT-N-01")

# ========== 설정 ==========
CSV_URL = "https://feedfiles.woolytech.com/nugnes-1920.myshopify.com/yH1YCJhVtJ.csv"  # 뉴네스 제공 CSV 다운로드 URL
EXPORT_DIR = "export/nugnes"  # JSON 저장 디렉토리
os.makedirs(EXPORT_DIR, exist_ok=True)
OUTPUT_JSON_PATH = os.path.join(EXPORT_DIR, "nugnes_processed_products.json")  # JSON 저장 경로
RETAILER_CODE = "IT-N-01"  # 거래처 코드
# ==========================

# ✅ 이미지 URL에서 대표 product_id 추출 (v= 뒤 숫자)
def extract_product_id(url):
    match = re.search(r"v=(\d+)", str(url))
    return match.group(1) if match else ""

# ✅ 링크에서 옵션의 variant ID 추출 (variant= 뒤 숫자)
def extract_option_id(url):
    match = re.search(r"variant=(\d+)", str(url))
    return match.group(1) if match else ""


# ✅ 비교용 정규화 함수 (None → "", str 처리)
def normalize(value):
    if value is None:
        return ""
    return str(value).strip()


# ✅ 대표상품 기준으로 옵션을 묶고 상품 정보 정리
def group_products(df):
    def build_product(group):
        row = group.iloc[0]  # 첫 번째 줄을 row 변수에 저장
        data = row.to_dict()
        total_quantity = 0
        options = []

        for _, row in group.iterrows():
            # ✅ 옵션 가격 결정: 옵션 price가 없으면 DISCOUNTED PRICE > PRICE 순서
            price = row.get("PRICE") or row.get("DISCOUNTED PRICE") or 0
            option = {
                "size": row.get("SIZE") or "",
                "stock": int(row.get("QUANTITY") or 0),
                "price": price,
                "option_id": row.get("option_id") or "",
                "variant_url": row.get("PRODUCT LINK") or "",
            }
            options.append(option)
            total_quantity += option["stock"]

        data["QUANTITY"] = total_quantity
        data["product_id"] = group["product_id"].iloc[0]
        data["options"] = options
        data["GENDER"] = row.get("GENDER") or ""
        data["GRUPPO SUPER"] = row.get("GRUPPO SUPER") or ""
        data["PRODUCT TYPE"] = row.get("PRODUCT TYPE") or ""
        data["COMPOSIZIONE"] = row.get("COMPOSIZIONE") or ""
        data["COLORE"] = row.get("COLORE") or ""        

        return data

    grouped = df[df["product_id"].notna()].groupby("product_id").apply(build_product).tolist()

    # ✅ NaN → 빈 문자열로 처리
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean(i) for i in obj]
        elif pd.isna(obj):
            return ""
        return obj

    return [clean(p) for p in grouped]

# ✅ 상품 및 옵션 DB에 등록 및 업데이트 수행 (최적화 방식 적용)
@transaction.atomic
def register_products(products):
    logger.info("🔄 DB 등록 시작")



    active_ids = [item["product_id"] for item in products if item.get("QUANTITY", 0) > 0]

    # ✅ 전체 기존 상품과 옵션 조회
    existing_products = RawProduct.objects.filter(retailer=RETAILER_CODE)
    existing_product_map = {p.external_product_id: p for p in existing_products}
    existing_options = RawProductOption.objects.filter(product__in=existing_products)
    existing_option_map = {(o.product.external_product_id, o.external_option_id): o for o in existing_options}

    products_to_create, products_to_update = [], []
    options_to_create, options_to_update = [], []
    updated_product_ids = set()

    for item in products:
        if int(item.get("QUANTITY", 0)) <= 0:
            continue  # ✅ 재고 없으면 무시

        external_id = item["product_id"]
        brand = item["BRAND"]
        model = item["CODICE PRODOTTO"]
        color_code = item["CODICE COLORE"]
        color_name = item.get("COLORE") or ""
        season = item["SEASON"]
        name = f"{brand} {item.get('PRODUCT TITLE', '')} {model} {color_code}"
        sku = f"{model} {color_code}"
        price_org = item.get("DISCOUNTED PRICE") or item.get("PRICE") or 0
        price_retail = item.get("PRICE") or 0

        # ✅ RawProduct 기본 필드 구성
        defaults = {
            "retailer": RETAILER_CODE,
            "raw_brand_name": brand,
            "product_name": name,
            "season": season,            
            "color": color_name,
            "sku": sku,
            "gender" : item.get("GENDER") or "",
            "category1": item.get("GRUPPO SUPER") or "",
            "category2": item.get("PRODUCT TYPE") or "",
            "origin": item.get("MADE IN") or "",
            "material": item.get("COMPOSIZIONE") or "",
            "description": item.get("DESCRIPTION 3") or "",
            "image_url_1": item.get("LINK IMMAGINE 1") or "",
            "image_url_2": item.get("LINK IMMAGINE 2") or "",
            "image_url_3": item.get("LINK IMMAGINE 3") or "",
            "image_url_4": item.get("LINK IMMAGINE 4") or "",
            "price_org": price_org,
            "price_retail": price_retail,
            "status": "pending",
        }

        existing = existing_product_map.get(external_id)
        if existing:
            changed = False
            for field, value in defaults.items():
                old = normalize(getattr(existing, field))
                new = normalize(value)
                if old != new:
                    setattr(existing, field, value)
                    changed = True
            if changed:
                products_to_update.append(existing)
            updated_product_ids.add(external_id)
        else:
            product = RawProduct(external_product_id=external_id, **defaults)
            products_to_create.append(product)

    # ✅ 상품 대량 처리
    RawProduct.objects.bulk_create(products_to_create, batch_size=500)
    RawProduct.objects.bulk_update(products_to_update, list(defaults.keys()), batch_size=500)

    # ✅ 새로 생성된 상품 포함 다시 조회하여 매핑
    all_products = RawProduct.objects.filter(retailer=RETAILER_CODE, external_product_id__in=active_ids)
    product_map = {p.external_product_id: p for p in all_products}

    for item in products:
        if int(item.get("QUANTITY", 0)) <= 0:
            continue


        product = product_map.get(item["product_id"])
        if not product:
            continue

        for opt in item["options"]:
            key = (product.external_product_id, opt["option_id"])
            existing = existing_option_map.get(key)
            stock = opt["stock"]
            price = opt["price"] or item.get("DISCOUNTED PRICE") or item.get("PRICE") or 0
            
            new_option_url = (opt.get("variant_url") or "").strip()


            if existing:
                old_option_url = (existing.option_url or "").strip()
                if (
                    existing.stock != stock
                    or str(existing.price) != str(price)
                    or old_option_url != new_option_url
                ):
                    existing.stock = stock
                    existing.price = price
                    existing.option_url = new_option_url
                    options_to_update.append(existing)
            else:
                options_to_create.append(RawProductOption(
                    product=product,
                    external_option_id=opt["option_id"],
                    option_name=opt["size"],
                    stock=stock,
                    price=price,
                    option_url=new_option_url,
                ))

    # ✅ 옵션 대량 처리
    RawProductOption.objects.bulk_create(options_to_create, batch_size=1000)
    RawProductOption.objects.bulk_update(options_to_update, ["stock", "price", "option_url"], batch_size=1000)

    # ✅ 누락된 상품은 soldout 처리 (오늘 수집에 포함 안된 기존 상품)
    RawProduct.objects.filter(retailer=RETAILER_CODE).exclude(external_product_id__in=active_ids).update(status="soldout")

    logger.info(f"✅ 상품 생성: {len(products_to_create)}개 / 수정: {len(products_to_update)}개")
    logger.info(f"✅ 옵션 생성: {len(options_to_create)}개 / 수정: {len(options_to_update)}개")
    logger.info(f"✅ soldout 처리됨: {existing_products.exclude(external_product_id__in=active_ids).count()}개")

# ✅ 전체 파이프라인 실행 함수
def main():
    logger.info("📦 뉴네스 상품 수집 및 등록 시작")

    # ✅ 1. CSV 파일 메모리에서 직접 읽기 (파일 저장 없이 처리)
    res = requests.get(CSV_URL)
    df = pd.read_csv(io.StringIO(res.content.decode("ISO-8859-1")))
    df.columns = df.columns.str.strip()

    # ✅ 2. ID 추출
    df["product_id"] = df["LINK IMMAGINE 1"].apply(extract_product_id)
    df["option_id"] = df["PRODUCT LINK"].apply(extract_option_id)

    # ✅ 3. 대표상품 + 옵션 묶기
    products = group_products(df)


    # ✅ 4. 중간 JSON 저장
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    # ✅ 5. DB 등록
    register_products(products)

    logger.info("🎉 모든 상품 처리 완료")
    return len(products)  # ✅ 수집한 상품 수 반환

if __name__ == "__main__":
    main()
