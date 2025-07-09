import sys
import os
import django
import requests
import logging
import time
from datetime import datetime, timedelta, timezone
from django.db import transaction
from typing import Dict, List, Optional, Tuple

# HTTPAdapter와 Retry를 올바르게 import
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Django 환경 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mallapi.settings")
django.setup()

from shop.models import RawProduct, RawProductOption

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gaudenzi_collector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class APIConfig:
    """API 설정 클래스"""
    def __init__(self):
        self.BASE_URL = "https://api.dresscode.cloud"
        self.CLIENT = "gaudenzi"
        self.CHANNEL_KEY = "33a2aaeb-7ef2-44c5-bb66-0d3a84e9869f"
        #self.SUBSCRIPTION_KEY = "8da6e776b61e4a56a2b2bed51c8199ea" #메인아이디 키
        self.SUBSCRIPTION_KEY = "d9b2538817b248d6a39e7289d5b87e87"  #서브아이디 키 = 해당키로 수짐 및 주문전송 예정
        self.RETAILER_CODE = "IT-G-03"
        self.TIMEOUT = 30
        self.MAX_RETRIES = 3
        self.BATCH_SIZE = 1000

config = APIConfig()

class APIClient:
    """API 클라이언트 클래스"""
    
    def __init__(self):
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """재시도 로직이 포함된 세션 생성"""
        session = requests.Session()
        
        # urllib3 버전에 따라 다른 파라미터 사용
        try:
            # 새로운 버전 (urllib3 >= 1.26)
            retry_strategy = Retry(
                total=config.MAX_RETRIES,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS"],
                backoff_factor=1
            )
        except TypeError:
            # 이전 버전 (urllib3 < 1.26)
            retry_strategy = Retry(
                total=config.MAX_RETRIES,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["HEAD", "GET", "OPTIONS"],
                backoff_factor=1
            )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def call_api(self, url: str, headers: dict, params: dict = None) -> Optional[dict]:
        """API 호출 메서드"""
        try:
            logger.info(f"📡 API 요청: {url}")
            logger.debug(f"🔍 파라미터: {params}")
            
            response = self.session.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=config.TIMEOUT
            )
            
            # 403 에러 특별 처리 (할당량 초과)
            if response.status_code == 403:
                error_data = response.json()
                message = error_data.get('message', '')
                
                # 할당량 초과 메시지에서 대기 시간 추출
                if "Out of call volume quota" in message:
                    import re
                    match = re.search(r'(\d{2}):(\d{2}):(\d{2})', message)
                    if match:
                        hours, minutes, seconds = map(int, match.groups())
                        wait_seconds = hours * 3600 + minutes * 60 + seconds + 60  # 여유 60초 추가
                        logger.warning(f"⏳ API 할당량 초과. {wait_seconds}초 ({wait_seconds//60}분) 대기 필요")
                        logger.info(f"💤 {datetime.now().strftime('%H:%M:%S')}부터 대기 시작...")
                        time.sleep(wait_seconds)
                        return self.call_api(url, headers, params)  # 재시도
                
                logger.error(f"❌ 403 에러: {message}")
                return None
            
            # 429 에러 특별 처리
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"⏳ Rate limit 도달. {retry_after}초 대기 필요")
                time.sleep(retry_after)
                return self.call_api(url, headers, params)  # 재시도
            
            response.raise_for_status()
            logger.info(f"✅ 응답 성공: {response.status_code}")
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ 타임아웃 발생: {url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP 에러: {e.response.status_code} - {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"🚨 요청 예외: {e}")
            return None
        except Exception as e:
            logger.error(f"💥 예상치 못한 에러: {e}")
            return None

class ProductCollector:
    """상품 수집 클래스"""
    
    def __init__(self):
        self.api_client = APIClient()
        self.stats = {
            "collected": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
            "skipped": 0
        }
    
    def fetch_products(self, from_datetime: str, to_datetime: str = None) -> Dict[str, int]:
        """상품 데이터 수집 - JSON 전체 반환"""
        logger.info(f"🔄 상품 수집 시작: from={from_datetime}")
        if to_datetime:
            logger.info(f"   to={to_datetime}")
        
        url = f"{config.BASE_URL}/channels/v2/api/feeds/en/clients/{config.CLIENT}/products"
        headers = {
            "Ocp-Apim-Subscription-Key": config.SUBSCRIPTION_KEY,
            "client": config.CLIENT,
            "Accept": "application/json"
        }
        params = {
            "channelKey": config.CHANNEL_KEY,
            "from": from_datetime
        }
        
        if to_datetime:
            params["to"] = to_datetime
        
        # API 호출
        data = self.api_client.call_api(url, headers, params)
        if not data:
            logger.warning("⚠️ API 응답 없음")
            return {"collected_count": 0, "registered_count": 0}
        
        # DressCode API는 data 배열에 상품 목록을 반환
        products = data.get("data", [])
        self.stats["collected"] = len(products)
        logger.info(f"📦 수집된 상품 수: {len(products)}개")
        
        if not products:
            return {"collected_count": 0, "registered_count": 0}
        
        return self._process_products(products)
    
    def _process_products(self, products: List[dict]) -> Dict[str, int]:
        """상품 데이터 처리 및 저장"""
        try:
            # 유효한 상품만 필터링
            valid_products = []
            for product in products:
                if self._validate_product(product):
                    valid_products.append(product)
                else:
                    self.stats["skipped"] += 1
            
            logger.info(f"✅ 유효한 상품: {len(valid_products)}개 / 스킵: {self.stats['skipped']}개")
            
            if not valid_products:
                return {"collected_count": len(products), "registered_count": 0}
            
            # 상품 저장
            created, updated = self._save_products(valid_products)
            
            # 옵션 저장
            self._save_product_options(valid_products)
            
            return {
                "collected_count": len(products),
                "registered_count": created + updated
            }
            
        except Exception as e:
            logger.error(f"💥 상품 처리 중 에러: {e}", exc_info=True)
            self.stats["errors"] += 1
            return {"collected_count": len(products), "registered_count": 0}
    
    def _validate_product(self, product: dict) -> bool:
        """상품 데이터 유효성 검증"""
        # 필수 필드 검증
        if not product.get("productID"):
            logger.warning("⚠️ productID 누락")
            return False
        
        if not product.get("brand") or not product.get("name"):
            logger.warning(f"⚠️ 필수 정보 누락 - ID: {product.get('productID')}")
            return False
        
        # 가격 유효성 검증
        try:
            price = float(product.get("price", 0))
            if price < 0:
                logger.warning(f"⚠️ 잘못된 가격: {price} - ID: {product.get('productID')}")
                return False
        except (ValueError, TypeError):
            logger.warning(f"⚠️ 가격 변환 실패 - ID: {product.get('productID')}")
            return False
        
        return True
    
    def _save_products(self, products: List[dict]) -> Tuple[int, int]:
        """상품 저장 - 기존 상품은 업데이트만"""
        external_ids = [p["productID"] for p in products]
        
        # 기존 상품 조회
        existing_products = {
            p.external_product_id: p
            for p in RawProduct.objects.filter(
                retailer=config.RETAILER_CODE,
                external_product_id__in=external_ids
            )
        }
        
        to_create, to_update = [], []
        
        for item in products:
            try:
                product_data = self._extract_product_data(item)
                external_id = product_data.pop("external_product_id")
                
                if external_id in existing_products:
                    # 🔄 기존 상품 업데이트
                    product = existing_products[external_id]
                    
                    # 변경된 필드만 업데이트
                    changed = False
                    for key, value in product_data.items():
                        if getattr(product, key) != value:
                            setattr(product, key, value)
                            changed = True
                    
                    if changed:
                        to_update.append(product)
                else:
                    # ✨ 신규 상품 생성
                    to_create.append(RawProduct(
                        retailer=config.RETAILER_CODE,
                        external_product_id=external_id,
                        **product_data
                    ))
            except Exception as e:
                logger.error(f"❌ 상품 처리 실패 - ID: {item.get('productID')}: {e}")
                self.stats["errors"] += 1
        
        # 데이터베이스 저장
        with transaction.atomic():
            if to_create:
                RawProduct.objects.bulk_create(to_create, batch_size=config.BATCH_SIZE)
                logger.info(f"✨ 신규 상품 생성: {len(to_create)}개")
            
            if to_update:
                # 업데이트할 필드 리스트 생성
                update_fields = [
                    "product_name", "raw_brand_name", "season", "gender",
                    "category1", "category2", "material", "origin",
                    "price_org", "price_supply", "price_retail", "sku",
                    "created_at", "image_url_1", "image_url_2",
                    "image_url_3", "image_url_4"
                ]
                RawProduct.objects.bulk_update(to_update, update_fields, batch_size=config.BATCH_SIZE)
                logger.info(f"🔄 기존 상품 업데이트: {len(to_update)}개")
        
        self.stats["created"] = len(to_create)
        self.stats["updated"] = len(to_update)
        
        return len(to_create), len(to_update)
    
    def _extract_product_data(self, item: dict) -> dict:
        """상품 데이터 추출"""
        # 안전한 데이터 추출
        def safe_get(d, key, default=""):
            return d.get(key) or default
        
        def safe_float(value, default=0):
            try:
                return float(value or 0)
            except (ValueError, TypeError):
                return default
        
        # 이미지 처리
        images = item.get("photos", [])
        image_data = {
            f"image_url_{i+1}": images[i] if i < len(images) else None
            for i in range(4)
        }
        
        # 날짜 처리
        created_at = item.get("productLastUpdated")
        if not created_at:
            created_at = datetime.now(timezone.utc).isoformat()
        
        return {
            "external_product_id": item["productID"],
            "product_name": f"{safe_get(item, 'brand')} {safe_get(item, 'name')} {safe_get(item, 'sku')}".strip(),
            "raw_brand_name": safe_get(item, "brand"),
            "season": safe_get(item, "season"),
            "gender": safe_get(item, "genre"),
            "category1": safe_get(item, "type"),
            "category2": safe_get(item, "category"),
            "material": safe_get(item, "composition"),
            "origin": safe_get(item, "madeIn"),
            "price_org": safe_float(item.get("wholesalePrice")),
            "price_supply": safe_float(item.get("price")),
            "price_retail": safe_float(item.get("retailPrice")),
            "sku": safe_get(item, "sku"),
            "created_at": created_at,
            **image_data
        }
    
    def _save_product_options(self, products: List[dict]) -> None:
        """상품 옵션 저장 - 기존 옵션은 업데이트만"""
        # 상품 맵 생성
        external_ids = [p["productID"] for p in products]
        product_map = {
            p.external_product_id: p
            for p in RawProduct.objects.filter(
                retailer=config.RETAILER_CODE,
                external_product_id__in=external_ids
            )
        }
        
        # 기존 옵션 조회
        existing_options = {
            opt.external_option_id: opt
            for opt in RawProductOption.objects.filter(
                product__in=product_map.values()
            )
            if opt.external_option_id
        }
        
        to_create, to_update = [], []
        
        for item in products:
            external_id = item["productID"]
            if external_id not in product_map:
                continue
            
            product = product_map[external_id]
            sizes = item.get("sizes", [])
            
            for opt in sizes:
                try:
                    option_data = self._extract_option_data(opt, product)
                    if not option_data:
                        continue
                    
                    barcode = option_data["external_option_id"]
                    
                    if barcode in existing_options:
                        # 🔄 기존 옵션 업데이트
                        existing = existing_options[barcode]
                        if (existing.stock != option_data["stock"] or 
                            existing.price != option_data["price"]):
                            existing.stock = option_data["stock"]
                            existing.price = option_data["price"]
                            to_update.append(existing)
                    else:
                        # ✨ 신규 옵션 생성
                        to_create.append(RawProductOption(**option_data))
                except Exception as e:
                    logger.error(f"❌ 옵션 처리 실패: {e}")
                    self.stats["errors"] += 1
        
        # 데이터베이스 저장
        with transaction.atomic():
            if to_create:
                RawProductOption.objects.bulk_create(to_create, batch_size=config.BATCH_SIZE)
                logger.info(f"✨ 신규 옵션 생성: {len(to_create)}개")
            
            if to_update:
                RawProductOption.objects.bulk_update(
                    to_update, 
                    ["stock", "price"], 
                    batch_size=config.BATCH_SIZE
                )
                logger.info(f"🔄 기존 옵션 업데이트: {len(to_update)}개")
    
    def _extract_option_data(self, opt: dict, product: RawProduct) -> Optional[dict]:
        """옵션 데이터 추출"""
        barcode = opt.get("gtin")
        if not barcode:
            return None
        
        try:
            stock = max(0, int(opt.get("stock", 0)))  # 음수 재고 방지
            price = float(opt.get("price", 0))
            
            if price < 0:
                logger.warning(f"⚠️ 잘못된 옵션 가격: {price}")
                return None
            
        except (ValueError, TypeError):
            logger.warning(f"⚠️ 옵션 데이터 변환 실패: {barcode}")
            return None
        
        return {
            "product": product,
            "option_name": opt.get("size") or "ONE",
            "stock": stock,
            "price": price,
            "external_option_id": barcode
        }
    
    def print_summary(self):
        """수집 결과 요약 출력"""
        logger.info("=" * 60)
        logger.info("📊 수집 결과 요약")
        logger.info(f"  📦 수집된 상품: {self.stats['collected']}개")
        logger.info(f"  ✨ 신규 생성: {self.stats['created']}개")
        logger.info(f"  🔄 업데이트: {self.stats['updated']}개")
        logger.info(f"  ⏭️  스킵: {self.stats['skipped']}개")
        logger.info(f"  ❌ 에러 발생: {self.stats['errors']}개")
        logger.info("=" * 60)

def fetch_daily():
    """일일 수집 - 어제 데이터만"""
    logger.info("=" * 60)
    logger.info("⏱️  [일일 수집 모드] 어제 데이터 수집")
    logger.info("=" * 60)
    
    collector = ProductCollector()
    
    # 어제 00:00부터
    yesterday = datetime.now(timezone.utc) - timedelta(days=2)
    from_str = yesterday.strftime("%Y-%m-%dT00:00:00.000Z")
    
    result = collector.fetch_products(from_str)
    collector.print_summary()
    
    return result

def fetch_full_history(days: int = 6):
    """전체 이력 수집 - 한 번에 수집"""
    logger.info("=" * 60)
    logger.info(f"🗂️  [최근 {days}일 수집 모드] 시작")
    logger.info("=" * 60)
    
    collector = ProductCollector()
    
    # 시작 날짜 계산 (days일 전부터)
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    from_str = start_date.strftime("%Y-%m-%dT00:00:00.000Z")
    
    logger.info(f"📅 {start_date.strftime('%Y-%m-%d')}부터 오늘까지 데이터 수집 중...")
    
    try:
        # 한 번의 API 호출로 전체 기간 수집
        result = collector.fetch_products(from_str)
        collector.print_summary()
        
        return {
            "collected_count": result.get("collected_count", 0),
            "registered_count": result.get("registered_count", 0)
        }
        
    except Exception as e:
        logger.error(f"❌ 수집 실패: {e}", exc_info=True)
        collector.print_summary()
        
        return {
            "collected_count": 0,
            "registered_count": 0
        }

def main():
    """메인 함수"""
    try:
        start_time = time.time()
        
        if "--full" in sys.argv:
            # 일수 파라미터 지원
            days = 6
            for arg in sys.argv:
                if arg.startswith("--days="):
                    try:
                        days = int(arg.split("=")[1])
                        if days <= 0 or days > 365:
                            logger.error("❌ 일수는 1~365 사이여야 합니다.")
                            return
                    except ValueError:
                        logger.error("❌ 잘못된 일수 형식")
                        return
            
            result = fetch_full_history(days)
        else:
            result = fetch_daily()
        
        # 실행 시간 출력
        elapsed_time = time.time() - start_time
        logger.info(f"\n⏱️  총 실행 시간: {elapsed_time:.2f}초")
        
        # 종료 메시지
        if result.get("collected_count", 0) > 0:
            logger.info("✅ 수집 완료!")
        else:
            logger.warning("⚠️  수집된 상품이 없습니다.")
    
    except KeyboardInterrupt:
        logger.info("\n⚠️  사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"\n💥 예상치 못한 오류: {e}", exc_info=True)

if __name__ == "__main__":
    main()