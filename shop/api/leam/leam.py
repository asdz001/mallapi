import requests
import os
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from shop.models import RawProduct, RawProductOption, Retailer
from django.db import transaction
from django.utils.timezone import now
from django.conf import settings
import time
import hashlib
from pathlib import Path
import logging
import psutil
import gc

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RETAILER_CODE = "IT-L-01"
BASE_URL = "https://srv2.best-fashion.net"
TOKEN = "292ae87edb8e5f2a15dd489f5c10b4b9"

EXPORT_DIR = "export/leam"
IMAGE_SAVE_DIR = "media/leam"
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)

# 🚀 개선된 이미지 다운로드 설정
MAX_WORKERS = 50  # 병렬 처리 스레드 수
TIMEOUT = 15      # 네트워크 타임아웃
RETRY_COUNT = 2   # 재시도 횟수
CHUNK_SIZE = 8192 # 스트리밍 다운로드 청크 크기

# 🎯 이미지 포맷 설정 (settings.py에서 제어)
USE_WEBP = getattr(settings, 'USE_WEBP', True) # settings.py에서 제어 가능
WEBP_QUALITY = getattr(settings, 'WEBP_QUALITY', 85) # WebP 품질 설정
JPEG_QUALITY = getattr(settings, 'JPEG_QUALITY', 80) # JPEG 품질 설정
SAVE_BOTH_FORMATS = getattr(settings, 'SAVE_BOTH_FORMATS', False) # 설정에 따라 WebP와 JPEG 모두 저장 - False로 설정 시 WebP만 저장

# 🔧 캐시된 세션 생성 (연결 재사용)
def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'LeamImageDownloader/2.0',
        'Accept': 'image/*',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    })
    # 연결 풀 최적화
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=100,
        pool_maxsize=100,
        max_retries=RETRY_COUNT
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# 전역 세션 (스레드 안전)
session = create_session()

def get_image_base_url() -> str:
    """이미지 베이스 URL 조회"""
    try:
        url = f"{BASE_URL}/ApiV3/token/{TOKEN}"
        res = session.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        image_prefix = data.get("image_url", "").strip("/")

        if image_prefix.startswith("http"):
            return image_prefix
        return f"https://{image_prefix}"
    
    except Exception as e:
        logger.error(f"이미지 base URL 요청 실패: {e}")
        return "https://srv2.best-fashion.net/img"

def fetch_all_products() -> List[Dict]:
    """전체 상품 목록 수집"""
    logger.info("📡 Leam 상품 수집 시작...")
    url = f"{BASE_URL}/ApiV3/token/{TOKEN}/callType/allStockGroup"
    try:
        res = session.get(url, timeout=30)
        res.raise_for_status()
        products = res.json()
        product_list = products.get("products", [])

        with open(os.path.join(EXPORT_DIR, "leam_full_catalog.json"), "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 총 {len(product_list)}개 상품 수집 완료")
        return product_list
    except Exception as e:
        logger.error(f"상품 수집 실패: {e}")
        return []

def build_media_url(path: str) -> str:
    """
    설정에 따른 이미지 URL 생성
    """
    if not path:
        return ""
    
    path_obj = Path(path)
    
    if USE_WEBP:
        # WebP 확장자로 변경
        webp_path = str(path_obj.with_suffix('.webp'))
        return f"{settings.MEDIA_URL.rstrip('/')}/{webp_path.lstrip('/')}"
    else:
        # JPEG 확장자로 변경
        jpeg_path = str(path_obj.with_suffix('.jpg'))
        return f"{settings.MEDIA_URL.rstrip('/')}/{jpeg_path.lstrip('/')}"

def convert_leam_to_raw_format(raw_data: List[Dict]) -> List[Dict]:
    """Leam API 데이터를 내부 포맷으로 변환"""
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
                    "price": float(item.get("price", 0)),
                    "external_option_id": opt.get("stock_id", "")
                }
                for opt in item["available_size"]
            ]
        }
        converted.append(product)
    return converted

def get_existing_image_files(folder_name: str) -> set:
    """폴더 내 기존 이미지 파일명 조회 (중복 다운로드 방지)"""
    folder_path = Path(IMAGE_SAVE_DIR) / folder_name
    if not folder_path.exists():
        return set()
    
    existing_files = set()
    for ext in ['.webp', '.jpg', '.jpeg', '.png']:
        existing_files.update(f.stem for f in folder_path.glob(f'*{ext}'))
    return existing_files

def monitor_performance() -> float:
    """시스템 성능 모니터링"""
    memory_percent = psutil.virtual_memory().percent
    if memory_percent > 80:
        logger.warning(f"⚠️ 메모리 사용률 높음: {memory_percent:.1f}%")
        gc.collect()  # 가비지 컬렉션 강제 실행
    return memory_percent

def download_image_optimized(
    image_name: str, 
    base_url: str, 
    folder_name: str, 
    resize_width: int = 1200, 
    force: bool = False
) -> Tuple[str, bool, str]:
    """
    최적화된 이미지 다운로드 함수 (설정 기반)
    Returns: (save_path, success, error_msg)
    """
    if not image_name:
        return "", False, "이미지명 없음"

    folder_path = Path(IMAGE_SAVE_DIR) / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # 원본 파일명에서 확장자 분리
    name_without_ext = Path(image_name).stem
    
    # 설정에 따른 파일 경로 결정
    if USE_WEBP:
        target_path = folder_path / f"{name_without_ext}.webp"
        fallback_path = folder_path / f"{name_without_ext}.jpg"
    else:
        target_path = folder_path / f"{name_without_ext}.jpg"
        fallback_path = None
    
    # 파일 존재 체크 (force가 False일 때만)
    if not force and target_path.exists():
        return str(target_path), True, f"{'WebP' if USE_WEBP else 'JPEG'} 이미 존재"

    url = f"{base_url}/{image_name}"
    
    for attempt in range(RETRY_COUNT + 1):
        try:
            # 🚀 스트리밍 다운로드로 메모리 효율성 증대
            response = session.get(url, timeout=TIMEOUT, stream=True)
            response.raise_for_status()
            
            # Content-Length 체크 (너무 작은 파일 거부)
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) < 1024:  # 1KB 미만
                return "", False, "파일 크기가 너무 작음"

            # 🚀 메모리 효율적인 이미지 처리
            image_data = BytesIO()
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    image_data.write(chunk)
            
            image_data.seek(0)
            image = Image.open(image_data)
            
            # 이미지 포맷 체크
            if image.format not in ['JPEG', 'PNG', 'WEBP', 'BMP']:
                return "", False, f"지원하지 않는 포맷: {image.format}"

            # 🚀 리사이징 최적화 (필요할 때만)
            if image.width > resize_width:
                height = int(resize_width * image.height / image.width)
                image = image.resize((resize_width, height), Image.Resampling.LANCZOS)

            # ✅ 설정에 따른 이미지 저장
            if USE_WEBP:
                # WebP 저장 시도
                try:
                    # RGBA 모드 유지 (WebP는 투명도 지원)
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    
                    image.save(
                        target_path, 
                        'WEBP', 
                        optimize=True, 
                        quality=WEBP_QUALITY, 
                        method=6,  # 최고 압축률
                        lossless=False
                    )
                    return str(target_path), True, "WebP 저장 성공"
                    
                except Exception as webp_error:
                    # WebP 실패 시 JPEG로 폴백
                    logger.warning(f"WebP 저장 실패, JPEG로 저장: {webp_error}")
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    image.save(
                        fallback_path, 
                        'JPEG', 
                        optimize=True, 
                        quality=JPEG_QUALITY, 
                        progressive=True
                    )
                    return str(fallback_path), True, "JPEG 폴백 저장"
            else:
                # JPEG 저장
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                image.save(
                    target_path, 
                    'JPEG', 
                    optimize=True, 
                    quality=JPEG_QUALITY, 
                    progressive=True
                )
                return str(target_path), True, "JPEG 저장 성공"
            
        except requests.exceptions.Timeout:
            if attempt < RETRY_COUNT:
                time.sleep(0.5 * (attempt + 1))  # 지수 백오프
                continue
            return "", False, f"타임아웃 (시도: {attempt + 1}회)"
        except requests.exceptions.RequestException as e:
            if attempt < RETRY_COUNT:
                time.sleep(0.5 * (attempt + 1))
                continue
            return "", False, f"네트워크 오류: {str(e)}"
        except Exception as e:
            return "", False, f"처리 오류: {str(e)}"
    
    return "", False, "모든 재시도 실패"

def save_images_for_products_optimized(products: List[Dict], batch_size: int = 50):
    """배치 단위로 이미지를 처리하여 메모리 사용량 최적화"""
    base_url = get_image_base_url()
    
    # DB에 이미 존재하는 상품 필터링
    existing_ids = set(
        RawProduct.objects.filter(retailer=RETAILER_CODE)
        .values_list("external_product_id", flat=True)
    )

    # ✅ 개선: 폴더별 기존 파일 캐시 생성
    folder_file_cache = {}
    
    # 다운로드할 이미지 작업 목록 생성
    tasks = []
    skipped_count = 0
    file_exists_count = 0
    
    for product in products:
        ext_id = product["external_product_id"]
        
        # DB에 있으면 이미지 다운로드 생략
        if ext_id in existing_ids:
            skipped_count += 1
            continue

        folder_name = product.get("image_folder", "")
        
        # ✅ 폴더별 기존 파일 캐시 활용
        if folder_name not in folder_file_cache:
            folder_file_cache[folder_name] = get_existing_image_files(folder_name)
        
        existing_files = folder_file_cache[folder_name]
        
        for i in range(1, 5):
            image_path = product.get(f"image_url_{i}")
            if image_path:
                image_name = os.path.basename(image_path)
                file_stem = Path(image_name).stem
                
                # ✅ 파일이 이미 존재하면 스킵
                if file_stem in existing_files:
                    file_exists_count += 1
                    continue
                    
                tasks.append((image_name, base_url, folder_name))

    total_images = len(tasks)
    logger.info(f"📥 이미지 다운로드 시작: {total_images}개")
    logger.info(f"⏭️ 스킵된 항목: DB상품 {skipped_count}개, 기존파일 {file_exists_count}개")
    
    if not tasks:
        logger.info("⏭️ 다운로드할 이미지가 없습니다")
        return

    # 🚀 배치 단위로 처리
    success_count = 0
    error_count = 0
    
    for i in range(0, len(tasks), batch_size):
        batch_tasks = tasks[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(tasks) + batch_size - 1) // batch_size
        
        logger.info(f"🔄 배치 {batch_num}/{total_batches} 처리 중... ({len(batch_tasks)}개 이미지)")
        
        # 성능 모니터링
        memory_usage = monitor_performance()
        
        # 배치 내에서 병렬 처리
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_task = {
                executor.submit(download_image_optimized, *task, force=True): task 
                for task in batch_tasks
            }
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    save_path, success, msg = future.result()
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        logger.warning(f"❌ {task[0]}: {msg}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ {task[0]}: 예외 발생 - {e}")
        
        # 배치 간 짧은 휴식 (서버 부하 방지)
        if i + batch_size < len(tasks):
            time.sleep(0.1)
        
        # 중간 진행률 보고
        progress = (i + batch_size) / len(tasks) * 100
        logger.info(f"📊 진행률: {progress:.1f}% | 성공: {success_count}, 실패: {error_count}")
    
    logger.info(f"✅ 이미지 다운로드 완료: 성공 {success_count}개, 실패 {error_count}개")

def save_images_for_products(products: List[Dict]):
    """기존 함수와 호환성을 위한 래퍼"""
    save_images_for_products_optimized(products)

def register_raw_products_bulk(products: List[Dict]):
    """DB 저장 처리: 신규/수정/품절"""
    
    # 거래처 객체 조회
    retailer = Retailer.objects.get(code=RETAILER_CODE)
    
    # 수집한 상품 ID만 추출
    incoming_ids = [p["external_product_id"] for p in products]
    
    # 기존 상품 조회 (업데이트 대상만)
    existing_products = RawProduct.objects.filter(
        retailer=retailer,
        external_product_id__in=incoming_ids
    )
    existing_map = {p.external_product_id: p for p in existing_products}

    # 전체 상품 ID만 추출 (soldout 판별용)
    all_existing_ids = set(
        RawProduct.objects.filter(retailer=retailer)
        .values_list("external_product_id", flat=True)
    )

    # 신규/수정 대상 분류
    new_products = []
    update_products = []
    updated_options = []
    new_options = []

    now_dt = now()

    for p in products:
        external_id = p["external_product_id"]

        if external_id in existing_map:
            # 기존 상품 업데이트
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
            # 신규 상품 등록
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

            # 신규 상품 옵션
            for opt in p["options"]:
                new_options.append(RawProductOption(
                    product=new_obj,
                    option_name=opt["option_name"],
                    stock=opt["stock"],
                    price=opt["price"],
                    external_option_id=opt["external_option_id"]
                ))

    # 🚀 DB 저장 작업: 트랜잭션으로 안전하게 처리
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

        # 수집되지 않은 기존 상품 → soldout 처리
        missing_ids = all_existing_ids - set(incoming_ids)
        RawProduct.objects.filter(
            retailer=retailer,
            external_product_id__in=missing_ids
        ).update(status="soldout", updated_at=now_dt)

    logger.info(f"✅ 신규: {len(new_products)}개 | 수정: {len(update_products)}개 | 품절: {len(missing_ids)}개")
    return len(new_products) + len(update_products)

def main():
    """메인 실행 함수"""
    start_time = time.time()
    
    try:
        logger.info(f"🚀 Leam 상품 수집 시작 (WebP: {USE_WEBP}, 품질: {WEBP_QUALITY if USE_WEBP else JPEG_QUALITY})")
        
        # 1. 상품 데이터 수집
        raw_data = fetch_all_products()
        if not raw_data:
            logger.error("❌ 상품 수집 실패")
            return 0, 0
        
        # 2. 데이터 변환
        mapped = convert_leam_to_raw_format(raw_data)
        logger.info(f"📝 변환 완료: {len(mapped)}개 상품")
        
        # 3. 이미지 다운로드
        image_start = time.time()
        save_images_for_products(mapped)
        image_elapsed = time.time() - image_start
        logger.info(f"🖼️ 이미지 처리 완료: {image_elapsed:.1f}초")
        
        # 4. DB 저장
        db_start = time.time()
        saved_count = register_raw_products_bulk(mapped)
        db_elapsed = time.time() - db_start
        logger.info(f"💾 DB 저장 완료: {db_elapsed:.1f}초")
        
        # 5. 최종 결과
        end_time = time.time()
        total_elapsed = end_time - start_time
        
        logger.info(f"🎉 전체 처리 완료!")
        logger.info(f"⏱️ 총 소요시간: {total_elapsed:.1f}초")
        logger.info(f"📊 처리 결과: 총 {len(mapped)}개, DB 저장 {saved_count}개")
        logger.info(f"🚄 평균 처리속도: {len(mapped)/total_elapsed:.1f}개/초")
        
        return len(mapped), saved_count
        
    except Exception as e:
        logger.error(f"💥 처리 중 치명적 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise