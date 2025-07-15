from shop.models import RawProduct, Product, RawProductOption, ProductOption
from django.db import transaction
from django.utils.timezone import now
from django.db.models import Sum, Prefetch, Q
from dictionary.models import BrandAlias, CategoryLevel1Alias, CategoryLevel2Alias, CategoryLevel3Alias
from pricing.models import FixedCountry, CountryAlias
from eventlog.services.log_service import log_conversion_failure
from typing import Dict, List, Optional, Tuple
import logging
from utils.product_logger import get_product_logger
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

class UltraOptimizedConversionService:
    """대폭 최적화된 변환 서비스 클래스"""
    
    def __init__(self, logger=None):
        # 로거 설정 - 전달받거나 기본 로거 사용
        self.logger = logger or get_product_logger("CONVERSION")        
        self.brand_cache = {}
        self.category1_cache = {}
        self.category2_cache = {}
        self.category3_cache = {}
        self.country_cache = {}
        
        # 통계
        self.stats = {
            'total_processed': 0,
            'success_count': 0,
            'fail_count': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'start_time': None,
            'db_queries': 0,
            'bulk_creates': 0,
            'bulk_updates': 0
        }
        
        self._load_all_caches()
    
    def _load_all_caches(self):
        """모든 매핑 데이터를 메모리에 캐시"""
        start_time = time.time()
        self.logger.info("🔄 매핑 데이터 캐시 로딩 중...")
        
        # 🚀 브랜드 캐시 - select_related로 쿼리 최적화
        brand_aliases = BrandAlias.objects.select_related('brand').all()
        for alias_obj in brand_aliases:
            aliases = [alias.strip().upper() for alias in alias_obj.alias.split(",")]
            for alias in aliases:
                self.brand_cache[alias] = alias_obj.brand.name
        
        # 🚀 카테고리 캐시들
        cat1_aliases = CategoryLevel1Alias.objects.select_related('category').all()
        for alias_obj in cat1_aliases:
            aliases = [alias.strip().upper() for alias in alias_obj.alias.split(",")]
            for alias in aliases:
                self.category1_cache[alias] = alias_obj.category.name
        
        cat2_aliases = CategoryLevel2Alias.objects.select_related('category').all()
        for alias_obj in cat2_aliases:
            aliases = [alias.strip().upper() for alias in alias_obj.alias.split(",")]
            for alias in aliases:
                self.category2_cache[alias] = alias_obj.category.name
        
        cat3_aliases = CategoryLevel3Alias.objects.select_related('category').all()
        for alias_obj in cat3_aliases:
            aliases = [alias.strip().upper() for alias in alias_obj.alias.split(",")]
            for alias in aliases:
                self.category3_cache[alias] = alias_obj.category.name
        
        # 🚀 국가 캐시
        country_aliases = CountryAlias.objects.select_related('standard_country').all()
        for alias_obj in country_aliases:
            aliases = [alias.strip().upper() for alias in alias_obj.origin_name.split(",")]
            for alias in aliases:
                self.country_cache[alias] = alias_obj.standard_country.name
        
        elapsed = time.time() - start_time
        self.logger.info(f"✅ 캐시 로딩 완료 ({elapsed:.2f}초)")
        self.logger.info(f"   브랜드: {len(self.brand_cache)}개")
        self.logger.info(f"   카테고리1: {len(self.category1_cache)}개")
        self.logger.info(f"   카테고리2: {len(self.category2_cache)}개")
        self.logger.info(f"   카테고리3: {len(self.category3_cache)}개")
        self.logger.info(f"   국가: {len(self.country_cache)}개")
    
    def match_brand_cached(self, input_value: str) -> Optional[str]:
        """캐시된 브랜드 매칭"""
        if not input_value:
            return None
        
        value = input_value.strip().upper()
        result = self.brand_cache.get(value)
        
        if result:
            self.stats['cache_hits'] += 1
        else:
            self.stats['cache_misses'] += 1
        
        return result
    
    def match_category_cached(self, cache_dict: Dict, input_value: str) -> Optional[str]:
        """캐시된 카테고리 매칭"""
        if not input_value:
            return None
        
        value = input_value.strip().upper()
        result = cache_dict.get(value)
        
        if result:
            self.stats['cache_hits'] += 1
        else:
            self.stats['cache_misses'] += 1
        
        return result
    
    def match_country_cached(self, input_value: str) -> Optional[str]:
        """캐시된 국가 매칭"""
        if not input_value:
            return None
        
        value = input_value.strip().upper()
        result = self.country_cache.get(value)
        
        if result:
            self.stats['cache_hits'] += 1
        else:
            self.stats['cache_misses'] += 1
        
        return result
    
    def bulk_convert_ultra_optimized(self, queryset, batch_size: int = 500) -> Tuple[int, int]:
        """🚀 대폭 최적화된 대량 변환 - 전체 재작성"""
        self.stats['start_time'] = time.time()
        self.logger.info("🚀 대폭 최적화된 대량 변환 시작...")
        
        # 🔥 1단계: 모든 기존 Product와 Option 미리 로드 (한 번에 가져오기)
        self.logger.info("📊 기존 데이터 로드 중...")
        existing_products = {}
        existing_options = {}
        
        for product in Product.objects.all().iterator(chunk_size=1000):
            existing_products[product.external_product_id] = product
        
        for option in ProductOption.objects.select_related('product').iterator(chunk_size=2000):
            key = (option.product.external_product_id, option.option_name)
            existing_options[key] = option
        
        self.logger.info(f"📊 기존 데이터 로드 완료: 상품 {len(existing_products)}개, 옵션 {len(existing_options)}개")
        
        # 🔥 2단계: 원본 데이터를 배치로 처리
        products_to_create = []
        products_to_update = []
        options_to_create = []
        options_to_update = []
        
        success_count = 0
        fail_count = 0
        processed_count = 0
        
        # 🚀 쿼리 최적화 - 재고 있는 것만 처리
        valid_queryset = queryset.filter(
            Q(options__stock__gt=0) & Q(price_org__gt=0)
        ).prefetch_related('options').distinct()
        
        total_count = valid_queryset.count()
        self.logger.info(f"📊 처리 대상: {total_count}개 상품")
        
        # 🔥 3단계: 배치 단위로 처리
        batch_num = 0
        for batch_start in range(0, total_count, batch_size):
            batch_num += 1
            batch = valid_queryset[batch_start:batch_start + batch_size]
            
            self.logger.info(f"🔄 배치 {batch_num} 처리 중... ({len(batch)}개)")
            
            # 배치 내 상품들 처리
            batch_success = 0
            batch_fail = 0
            
            for raw_product in batch:
                processed_count += 1
                self.stats['total_processed'] += 1
                
                # 🚀 빠른 검증 (재고와 가격만 체크)
                total_stock = sum(opt.stock for opt in raw_product.options.all())
                if total_stock <= 0 or not raw_product.price_org or raw_product.price_org <= 0:
                    batch_fail += 1
                    fail_count += 1
                    self.stats['fail_count'] += 1
                    continue
                
                # 🚀 매핑 수행 (캐시 사용)
                std_brand = self.match_brand_cached(raw_product.raw_brand_name)
                std_cat1 = self.match_category_cached(self.category1_cache, raw_product.gender)
                std_cat2 = self.match_category_cached(self.category2_cache, raw_product.category1)
                std_cat3 = self.match_category_cached(self.category3_cache, raw_product.category2)
                
                origin_input = (raw_product.origin or "").strip()
                std_origin = self.match_country_cached(origin_input) if origin_input else "-"
                
                # 필수 매핑 실패시 스킵
                if not std_brand or not std_cat1:
                    batch_fail += 1
                    fail_count += 1
                    self.stats['fail_count'] += 1
                    continue
                
                # 🚀 Product 처리 (기존 것 있으면 업데이트, 없으면 생성 준비)
                external_id = raw_product.external_product_id
                
                product_data = {
                    'retailer': raw_product.retailer,
                    'season': raw_product.season,
                    'gender': std_cat1,
                    'category1': std_cat2,
                    'category2': std_cat3,
                    'image_url': raw_product.image_url_1,
                    'raw_brand_name': raw_product.raw_brand_name,
                    'brand_name': std_brand,
                    'product_name': raw_product.product_name,
                    'sku': raw_product.sku,
                    'price_retail': raw_product.price_retail,
                    'price_org': raw_product.price_org,
                    'discount_rate': raw_product.discount_rate or 0,
                    'color': raw_product.color,
                    'material': raw_product.material,
                    'origin': std_origin or origin_input or "-",
                    'status': 'active',
                    'updated_at': now(),
                }
                
                if external_id in existing_products:
                    # 기존 상품 업데이트 준비
                    existing_product = existing_products[external_id]
                    for key, value in product_data.items():
                        setattr(existing_product, key, value)
                    products_to_update.append(existing_product)
                else:
                    # 새 상품 생성 준비
                    new_product = Product(
                        external_product_id=external_id,
                        created_at=raw_product.created_at or now(),
                        **product_data
                    )
                    products_to_create.append(new_product)
                    existing_products[external_id] = new_product  # 캐시에도 추가
                
                # 🚀 Option 처리 (재고 있는 것만)
                for raw_option in raw_product.options.filter(stock__gt=0):
                    option_key = (external_id, raw_option.option_name)
                    
                    option_data = {
                        'external_option_id': raw_option.external_option_id,
                        'stock': raw_option.stock,
                        'price': raw_option.price,
                        'option_url': raw_option.option_url or "",
                    }
                    
                    if option_key in existing_options:
                        # 기존 옵션 업데이트 준비
                        existing_option = existing_options[option_key]
                        for key, value in option_data.items():
                            setattr(existing_option, key, value)
                        options_to_update.append(existing_option)
                    else:
                        # 새 옵션 생성 준비
                        new_option = ProductOption(
                            product=existing_products[external_id],
                            option_name=raw_option.option_name,
                            **option_data
                        )
                        options_to_create.append(new_option)
                        existing_options[option_key] = new_option  # 캐시에도 추가
                
                batch_success += 1
                success_count += 1
                self.stats['success_count'] += 1
            
            # 🔥 4단계: 배치 단위로 DB에 저장 (트랜잭션)
            if products_to_create or products_to_update or options_to_create or options_to_update:
                with transaction.atomic():
                    # Product 대량 처리
                    if products_to_create:
                        Product.objects.bulk_create(products_to_create, batch_size=200)
                        self.stats['bulk_creates'] += len(products_to_create)
                        self.logger.info(f"  📥 Product 생성: {len(products_to_create)}개")
                        products_to_create = []
                    
                    if products_to_update:
                        Product.objects.bulk_update(
                            products_to_update, 
                            ['season', 'gender', 'category1', 'category2', 'image_url', 
                             'brand_name', 'product_name', 'sku', 'price_retail', 'price_org', 
                             'discount_rate', 'color', 'material', 'origin', 'status', 'updated_at'], 
                            batch_size=200
                        )
                        self.stats['bulk_updates'] += len(products_to_update)
                        self.logger.info(f"  🔄 Product 업데이트: {len(products_to_update)}개")
                        products_to_update = []
                    
                    # Option 대량 처리
                    if options_to_create:
                        ProductOption.objects.bulk_create(options_to_create, batch_size=500)
                        self.stats['bulk_creates'] += len(options_to_create)
                        self.logger.info(f"  📥 Option 생성: {len(options_to_create)}개")
                        options_to_create = []
                    
                    if options_to_update:
                        ProductOption.objects.bulk_update(
                            options_to_update,
                            ['external_option_id', 'stock', 'price', 'option_url'],
                            batch_size=500
                        )
                        self.stats['bulk_updates'] += len(options_to_update)
                        self.logger.info(f"  🔄 Option 업데이트: {len(options_to_update)}개")
                        options_to_update = []
                    
                    # RawProduct 상태 업데이트
                    success_raw_ids = [rp.id for rp in batch if rp.external_product_id in existing_products]
                    if success_raw_ids:
                        RawProduct.objects.filter(id__in=success_raw_ids).update(
                            status='converted', 
                            updated_at=now()
                        )
            
            # 진행률 보고
            progress = (processed_count / total_count) * 100
            elapsed = time.time() - self.stats['start_time']
            rate = processed_count / elapsed if elapsed > 0 else 0
            
            self.logger.info(f"  📊 배치 {batch_num} 완료: 성공 {batch_success}개, 실패 {batch_fail}개")
            self.logger.info(f"  📈 전체 진행률: {progress:.1f}% ({processed_count}/{total_count})")
            self.logger.info(f"  🚀 처리 속도: {rate:.1f}개/초")
        
        return success_count, fail_count
    
    def print_performance_stats(self):
        """성능 통계 출력"""
        elapsed = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        
        self.logger.info("=" * 60)
        self.logger.info("📊 변환 성능 통계")
        self.logger.info("=" * 60)
        self.logger.info(f"📦 총 처리: {self.stats['total_processed']:,}개")
        self.logger.info(f"✅ 성공: {self.stats['success_count']:,}개")
        self.logger.info(f"❌ 실패: {self.stats['fail_count']:,}개")
        
        if self.stats['total_processed'] > 0:
            success_rate = (self.stats['success_count'] / self.stats['total_processed']) * 100
            self.logger.info(f"📈 성공률: {success_rate:.1f}%")

        if elapsed > 0:
            rate = self.stats['total_processed'] / elapsed
            self.logger.info(f"⏱️ 총 소요 시간: {elapsed:.1f}초")
            self.logger.info(f"🚀 처리 속도: {rate:.1f}개/초")

        # 최적화 통계
        self.logger.info(f"🔥 대량 생성: {self.stats['bulk_creates']:,}개")
        self.logger.info(f"🔥 대량 업데이트: {self.stats['bulk_updates']:,}개")

        # 캐시 효율성
        total_lookups = self.stats['cache_hits'] + self.stats['cache_misses']
        if total_lookups > 0:
            cache_hit_rate = (self.stats['cache_hits'] / total_lookups) * 100
            self.logger.info(f"🎯 캐시 적중률: {cache_hit_rate:.1f}%")

        self.logger.info("=" * 60)


# 🚀 기존 OptimizedConversionService도 유지 (호환성)
class OptimizedConversionService(UltraOptimizedConversionService):
    """기존 서비스 (호환성 유지)"""
    def bulk_convert_optimized(self, queryset, batch_size: int = 2000) -> Tuple[int, int]:
        return self.bulk_convert_ultra_optimized(queryset, batch_size)


# 전역 서비스 인스턴스 (싱글톤 패턴)
_conversion_service = None

def get_conversion_service(logger=None):
    """변환 서비스 인스턴스 반환 (싱글톤)"""
    global _conversion_service
    if _conversion_service is None:
        _conversion_service = UltraOptimizedConversionService(logger=logger)
    return _conversion_service

# 거래처별 대량 변환 (최적화 버전)
def bulk_convert_or_update_products_by_retailer(retailer_code, batch_size=500):
    """🚀 대폭 최적화된 거래처별 대량 변환"""
    retailer_logger = get_product_logger(retailer_code)
    service = get_conversion_service(logger=retailer_logger)

    retailer_logger.info(f"🚀 [{retailer_code}] 대량 변환 시작...")

    raw_products = RawProduct.objects.filter(
        retailer=retailer_code,
        status__in=['pending', 'converted']
    )
    
    success_count, fail_count = service.bulk_convert_ultra_optimized(raw_products, batch_size)
    
    service.print_performance_stats()
    retailer_logger.info(f"✅ [{retailer_code}] 전송 완료 - 성공: {success_count}개 / 실패: {fail_count}개")
    
    return success_count

# 솔드아웃 처리
def sync_soldout_products_from_raw(retailer_code: str):
    """원본이 soldout인 상품 → 가공상품도 soldout 처리"""
    retailer_logger = get_product_logger(retailer_code)

    soldout_ids = RawProduct.objects.filter(
        retailer=retailer_code,
        status="soldout"
    ).values_list("external_product_id", flat=True)

    updated_count = Product.objects.filter(
        retailer=retailer_code,
        external_product_id__in=soldout_ids
    ).update(status="soldout")

    retailer_logger.info(f"🔁 가공상품 soldout 처리 완료: {updated_count}개")

# 기존 함수들 (호환성 유지)
def convert_or_update_product(raw_product):
    """기존 인터페이스 유지 - 단일 상품 변환"""
    service = get_conversion_service()
    return service.convert_single_product(raw_product)

def bulk_convert_or_update_products(batch_size=500):
    """기존 인터페이스 유지 - 전체 대량 변환"""
    service = get_conversion_service()
    
    logger.info("🚀 전체 대량 변환 시작...")
    
    raw_products = RawProduct.objects.filter(
        status__in=['pending', 'converted']
    )
    
    success_count, fail_count = service.bulk_convert_ultra_optimized(raw_products, batch_size)
    
    service.print_performance_stats()
    logger.info(f"✅ 전체 전송 완료 - 성공: {success_count}개 / 실패: {fail_count}개")
    
    return success_count