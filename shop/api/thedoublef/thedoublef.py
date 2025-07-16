"""
더블F 상품 통합 시스템
==================
CSV 수집 → 가공 → DB 등록
"""

import csv
import json
import requests
import os
from collections import defaultdict
from io import StringIO
from pathlib import Path
from django.db import transaction

# Django 모델 임포트
try:
    from shop.models import RawProduct, RawProductOption
    from utils.product_logger import get_product_logger
except ImportError:
    RawProduct = None
    RawProductOption = None
    get_product_logger = None

# 설정
CSV_URL = "https://feeds.datafeedwatch.com/48802/efbb59113adce323afff7639d3516691efec6e9c.csv"
RETAILER_CODE = "IT-F-01"
EXPORT_DIR = Path("export/thedoublef")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
JSON_PATH = EXPORT_DIR / "thedoublef_products.json"

def normalize_price(price_str):
    """EUR 670.08 → 670.08 (따옴표 제거 포함)"""
    if not price_str:
        return 0
    try:
        # 따옴표와 EUR 모두 제거
        clean_price = str(price_str).strip("'\"").replace("EUR", "").replace(",", "").strip()
        return float(clean_price) if clean_price else 0
    except:
        return 0

def extract_categories(product_type):
    """카테고리 분리: Apparel & Accessories > Clothing > Shirts & Tops"""
    if not product_type:
        return "", ""
    parts = product_type.split(" > ")
    category1 = parts[1].strip() if len(parts) > 1 else ""
    category2 = parts[2].strip() if len(parts) > 2 else ""
    return category1, category2

def clean_json_data(data):
    """JSON 데이터의 모든 값에서 따옴표 제거"""
    if isinstance(data, dict):
        return {key: clean_json_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [clean_json_data(item) for item in data]
    elif isinstance(data, str):
        # 문자열 값에서 앞뒤 따옴표 제거
        return data.strip("'\"").strip()
    else:
        return data

def collect_and_process(logger):
    """1단계: CSV 수집 → 가공 → JSON 저장"""
    logger.info("📥 CSV 수집 및 가공 시작")
    
    # CSV 다운로드
    response = requests.get(CSV_URL)
    response.raise_for_status()
    csv_text = response.content.decode("utf-8")
    logger.info(f"✅ CSV 다운로드 완료: {len(response.content)} bytes")
    
    # CSV 파싱 (파이프 구분자, 따옴표 제거 - KEY와 VALUE 모두)
    reader = csv.DictReader(StringIO(csv_text), delimiter="|")
    raw_data = []
    for row in reader:
        if row:
            # KEY와 VALUE 모두에서 따옴표 제거
            clean_row = {
                key.strip("'\"").strip(): value.strip("'\"").strip() if value else ""
                for key, value in row.items()
            }
            raw_data.append(clean_row)
    
    logger.info(f"📊 CSV 파싱 완료: {len(raw_data)}개 행")
    
    # 첫 번째 행 샘플 로그 (디버깅용)
    if raw_data:
        logger.info(f"🔍 샘플 데이터: {list(raw_data[0].items())[:3]}")
    
    # item_group_id 기준 그룹핑
    grouped = defaultdict(list)
    for row in raw_data:
        group_id = row.get("item_group_id", "").strip()
        if group_id:
            grouped[group_id].append(row)
    
    # 상품 구조화
    products = []
    for group_id, items in grouped.items():
        first = items[0]
        
        # 공통 정보
        product = {
            "item_group_id": group_id,
            "price": first.get("price", ""),
            "sale_price": first.get("sale_price", "")
        }
        
        # 공통 필드 추가 (옵션 필드 제외)
        exclude_fields = {"id", "size", "quantity", "gtin", "price", "sale_price"}
        for key, value in first.items():
            if key not in exclude_fields:
                product[key] = value
        
        # 옵션 정보
        product["options"] = [
            {
                "id": item.get("id", ""),
                "size": item.get("size", ""),
                "quantity": item.get("quantity", ""),
                "gtin": item.get("gtin", ""),
                "link": item.get("link", ""),
                "price": item.get("price", ""),
                "sale_price": item.get("sale_price", "")
            }
            for item in items
        ]
        
        products.append(product)
    
    logger.info(f"🔧 그룹핑 완료: {len(products)}개 상품")
    
    # ✅ JSON 저장 전에 모든 따옴표 제거
    clean_products = clean_json_data(products)
    
    # JSON 저장
    try:
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(clean_products, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 JSON 저장 (따옴표 제거 완료): {JSON_PATH}")
        return clean_products
    except Exception as e:
        logger.error(f"❌ JSON 저장 실패: {e}")
        return None

@transaction.atomic
def register_products(products_data, logger):
    """2단계: DB 등록"""
    logger.info(f"🔄 DB 등록 시작: {len(products_data)}개 상품")
    
    # 유효한 상품만
    valid_products = [p for p in products_data if p.get('item_group_id')]
    incoming_ids = [p['item_group_id'] for p in valid_products]
    
    # 기존 데이터 조회
    existing_products = {p.external_product_id: p for p in 
                        RawProduct.objects.filter(retailer=RETAILER_CODE, 
                                                 external_product_id__in=incoming_ids)}
    
    existing_options = {o.external_option_id: o for o in 
                       RawProductOption.objects.filter(
                           product__retailer=RETAILER_CODE,
                           product__external_product_id__in=incoming_ids
                       ).select_related('product')}
    
    # 상품 처리
    products_to_create = []
    products_to_update = []
    
    for product_data in valid_products:
        try:
            product_id = product_data['item_group_id']
            
            # 기본 정보
            brand = product_data.get("brand", "").strip()
            title = product_data.get("title", "").strip()
            article_code = product_data.get("article_code", "").strip()
            color_code = product_data.get("color_code", "").strip()
            
            # 가격
            price_retail = normalize_price(product_data.get("price", ""))
            sale_price = product_data.get("sale_price", "")
            price_org = normalize_price(sale_price) if sale_price else price_retail
            
            # 카테고리
            category1, category2 = extract_categories(product_data.get("product_type", ""))
            
            # 설명 (description + fit)
            desc_parts = []
            if product_data.get("description"):
                desc_parts.append(product_data["description"])
            if product_data.get("fit"):
                desc_parts.append(f"Fit: {product_data['fit']}")
            description = "\n".join(desc_parts)
            
            # 매핑된 데이터
            mapped_data = {
                'external_product_id': product_id,
                'retailer': RETAILER_CODE,
                'product_name': f"{brand} {title} {article_code} {color_code}".strip(),
                'raw_brand_name': brand,
                'sku': f"{article_code} {color_code}".strip(),
                'season': product_data.get("season", ""),
                'gender': product_data.get("gender", ""),
                'category1': category1,
                'category2': category2,
                'origin': product_data.get("made_in", ""),
                'material': product_data.get("material", ""),
                'color': product_data.get("color", ""),
                'description': description,
                'image_url_1': product_data.get("image_link", ""),
                'image_url_2': product_data.get("additional_image", ""),
                'image_url_3': "",
                'image_url_4': "",
                'price_org': price_org,
                'price_supply': price_org,
                'price_retail': price_retail,
                'status': 'pending'
            }
            
            if product_id in existing_products:
                # 업데이트
                existing = existing_products[product_id]
                for field, value in mapped_data.items():
                    if field != 'external_product_id':
                        setattr(existing, field, value)
                products_to_update.append(existing)
            else:
                # 신규 생성
                products_to_create.append(RawProduct(**mapped_data))
                
        except Exception as e:
            logger.error(f"❌ 상품 처리 실패 {product_id}: {e}")
    
    # 상품 저장
    if products_to_create:
        RawProduct.objects.bulk_create(products_to_create, batch_size=1000)
        logger.info(f"🆕 상품 생성: {len(products_to_create)}개")
    
    if products_to_update:
        update_fields = ['product_name', 'raw_brand_name', 'season', 'gender', 'category1', 
                        'category2', 'origin', 'material', 'color', 'description', 
                        'image_url_1', 'image_url_2', 'price_org', 'price_supply', 
                        'price_retail', 'sku', 'status']
        RawProduct.objects.bulk_update(products_to_update, update_fields, batch_size=1000)
        logger.info(f"🔄 상품 업데이트: {len(products_to_update)}개")
    
    # 현재 상품들 다시 조회
    current_products = {p.external_product_id: p for p in 
                       RawProduct.objects.filter(retailer=RETAILER_CODE, 
                                                external_product_id__in=incoming_ids)}
    
    # 옵션 처리
    options_to_create = []
    options_to_update = []
    incoming_option_ids = set()
    
    for product_data in valid_products:
        product_id = product_data['item_group_id']
        if product_id not in current_products:
            continue
        
        product_obj = current_products[product_id]
        
        for option_data in product_data.get('options', []):
            try:
                option_id = option_data.get("id", "")
                if not option_id:
                    continue
                
                # 옵션 가격 (더 명확한 로직)
                option_sale_price = option_data.get("sale_price", "").strip()
                option_price = option_data.get("price", "").strip()
                
                # 우선순위: 옵션 sale_price > 옵션 price > 상품 sale_price > 상품 price
                if option_sale_price:
                    price = normalize_price(option_sale_price)
                elif option_price:
                    price = normalize_price(option_price)
                else:
                    # 옵션에 가격이 없으면 상품 가격 사용
                    product_sale_price = product_data.get("sale_price", "").strip()
                    product_price = product_data.get("price", "").strip()
                    
                    if product_sale_price:
                        price = normalize_price(product_sale_price)
                    elif product_price:
                        price = normalize_price(product_price)
                    else:
                        price = 0
                
                # 재고 (문자열로 온 수량을 숫자로 변환)
                quantity_str = option_data.get("quantity", "0").strip()
                try:
                    stock = int(quantity_str) if quantity_str else 0
                except:
                    stock = 0
                
                mapped_option = {
                    'external_option_id': option_id,
                    'option_name': option_data.get("size", ""),
                    'stock': stock,
                    'price': price,
                    'option_url': option_data.get("link", "")
                }
                
                incoming_option_ids.add(option_id)
                
                if option_id in existing_options:
                    # 업데이트
                    existing = existing_options[option_id]
                    for field, value in mapped_option.items():
                        if field != 'external_option_id':
                            setattr(existing, field, value)
                    options_to_update.append(existing)
                else:
                    # 신규 생성
                    options_to_create.append(RawProductOption(
                        product=product_obj, **mapped_option
                    ))
                    
            except Exception as e:
                logger.error(f"❌ 옵션 처리 실패: {e}")
    
    # 옵션 저장
    if options_to_create:
        RawProductOption.objects.bulk_create(options_to_create, batch_size=1000)
        logger.info(f"🆕 옵션 생성: {len(options_to_create)}개")
    
    if options_to_update:
        RawProductOption.objects.bulk_update(options_to_update, 
                                           ['option_name', 'stock', 'price', 'option_url'], 
                                           batch_size=1000)
        logger.info(f"🔄 옵션 업데이트: {len(options_to_update)}개")
    
    # 옵션 삭제
    options_to_delete = [oid for oid, opt in existing_options.items() 
                        if opt.product.external_product_id in incoming_ids 
                        and oid not in incoming_option_ids]
    
    if options_to_delete:
        deleted_count = RawProductOption.objects.filter(
            external_option_id__in=options_to_delete
        ).delete()[0]
        logger.info(f"🗑️ 옵션 삭제: {deleted_count}개")
    
    # soldout 처리
    soldout_count = RawProduct.objects.filter(
        retailer=RETAILER_CODE
    ).exclude(
        external_product_id__in=incoming_ids
    ).exclude(
        status='soldout'
    ).update(status='soldout')
    
    if soldout_count > 0:
        logger.info(f"🧹 soldout 처리: {soldout_count}개")
    
    logger.info("✅ DB 등록 완료")
    return len(valid_products)

def main():
    """메인 실행 함수"""
    logger = get_product_logger(RETAILER_CODE)
    
    try:
        logger.info("🚀 더블F 통합 파이프라인 시작")
        
        # 1단계: 수집 및 가공
        collected_count = collect_and_process(logger)
        if collected_count <= 0:
            logger.error("❌ 수집 실패")
            return 0  # ✅ 수정: 0 반환
        
        # JSON에서 데이터 다시 로드
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                products_data = json.load(f)
        except Exception as e:
            logger.error(f"❌ JSON 로드 실패: {e}")
            return 0  # ✅ 수정: 0 반환
        
        # 2단계: DB 등록
        registered_count = register_products(products_data, logger)
        
        if registered_count > 0:
            logger.info(f"🎉 완료: {collected_count}개 상품 처리")
            
        else:
            logger.error("❌ 등록 실패")
            
        return collected_count  # ✅ 수정: 수집된 개수 반환
            
    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}")
        return 0  # ✅ 수정: 0 반환

# Django Command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = '더블F 상품 수집 및 등록'
    
    def handle(self, *args, **options):
        success = main()
        if success:
            self.stdout.write(self.style.SUCCESS('✅ 완료'))
        else:
            self.stdout.write(self.style.ERROR('❌ 실패'))

# 단독 실행
if __name__ == "__main__":
    import sys
    import django
    
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    sys.path.insert(0, BASE_DIR)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mallapi.settings")
    
    try:
        django.setup()
        from shop.models import RawProduct, RawProductOption
        from utils.product_logger import get_product_logger
        
        globals()['RawProduct'] = RawProduct
        globals()['RawProductOption'] = RawProductOption
        globals()['get_product_logger'] = get_product_logger
        
        success = main()
        print("🎉 성공" if success else "❌ 실패")
        
    except Exception as e:
        print(f"❌ 실행 실패: {e}")
        sys.exit(1)