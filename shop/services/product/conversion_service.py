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
    """
    대폭 최적화된 상품 변환 서비스
    
    주요 기능:
    1. 매핑 데이터 캐싱으로 DB 쿼리 최소화
    2. 대량 처리 최적화 (bulk_create/bulk_update)
    3. 메모리 효율적인 배치 처리
    4. 단순화된 로깅 시스템
    """
    
    def __init__(self, logger=None):
        # 로거 설정 - 전달받거나 기본 로거 사용
        self.logger = logger or get_product_logger("CONVERSION")
        
        # 매핑 데이터 캐시 (메모리에 저장하여 DB 쿼리 최소화)
        self.brand_cache = {}           # 브랜드 매핑: {원본명_대문자: 표준명}
        self.category1_cache = {}       # 카테고리1 매핑 (성별)
        self.category2_cache = {}       # 카테고리2 매핑 (대분류)
        self.category3_cache = {}       # 카테고리3 매핑 (소분류)
        self.country_cache = {}         # 국가 매핑: {원본명_대문자: 표준명}
        
        # 성능 통계 추적
        self.stats = {
            'total_processed': 0,       # 총 처리된 상품 수
            'success_count': 0,         # 성공한 변환 수
            'fail_count': 0,            # 실패한 변환 수
            'cache_hits': 0,            # 캐시 적중 횟수
            'cache_misses': 0,          # 캐시 미스 횟수
            'start_time': None,         # 처리 시작 시간
            'bulk_creates': 0,          # 대량 생성 레코드 수
            'bulk_updates': 0           # 대량 업데이트 레코드 수
        }
        
        # 초기화 시 모든 매핑 데이터를 메모리에 로드
        self._load_all_caches()
    
    def _load_all_caches(self):
        """
        모든 매핑 데이터를 메모리에 캐시
        
        처리 과정:
        1. 각 Alias 테이블에서 매핑 데이터 조회
        2. 쉼표로 구분된 별칭들을 파싱
        3. 대문자로 변환하여 캐시에 저장
        4. select_related로 관련 객체도 함께 조회하여 쿼리 최적화
        """
        start_time = time.time()
        
        # 브랜드 매핑 데이터 로드
        # BrandAlias.alias = "nike,나이키,NIKE" 형태를 파싱하여 각각 매핑
        brand_aliases = BrandAlias.objects.select_related('brand').all()
        for alias_obj in brand_aliases:
            aliases = [alias.strip().upper() for alias in alias_obj.alias.split(",")]
            for alias in aliases:
                self.brand_cache[alias] = alias_obj.brand.name
        
        # 카테고리1 매핑 데이터 로드 (주로 성별: 남성, 여성, 키즈 등)
        cat1_aliases = CategoryLevel1Alias.objects.select_related('category').all()
        for alias_obj in cat1_aliases:
            aliases = [alias.strip().upper() for alias in alias_obj.alias.split(",")]
            for alias in aliases:
                self.category1_cache[alias] = alias_obj.category.name
        
        # 카테고리2 매핑 데이터 로드 (대분류: 의류, 신발, 가방 등)
        cat2_aliases = CategoryLevel2Alias.objects.select_related('category').all()
        for alias_obj in cat2_aliases:
            aliases = [alias.strip().upper() for alias in alias_obj.alias.split(",")]
            for alias in aliases:
                self.category2_cache[alias] = alias_obj.category.name
        
        # 카테고리3 매핑 데이터 로드 (소분류: 티셔츠, 운동화, 백팩 등)
        cat3_aliases = CategoryLevel3Alias.objects.select_related('category').all()
        for alias_obj in cat3_aliases:
            aliases = [alias.strip().upper() for alias in alias_obj.alias.split(",")]
            for alias in aliases:
                self.category3_cache[alias] = alias_obj.category.name
        
        # 국가 매핑 데이터 로드
        # CountryAlias.origin_name = "한국,korea,KR" 형태를 파싱
        country_aliases = CountryAlias.objects.select_related('standard_country').all()
        for alias_obj in country_aliases:
            aliases = [alias.strip().upper() for alias in alias_obj.origin_name.split(",")]
            for alias in aliases:
                self.country_cache[alias] = alias_obj.standard_country.name
        
        elapsed = time.time() - start_time
        # 단순화된 로깅: 캐시 로딩 완료만 기록
        self.logger.info(f"🔄 매핑 데이터 캐시 로딩 완료 ({elapsed:.1f}초)")
    
    def match_brand_cached(self, input_value: str) -> Optional[str]:
        """
        캐시된 브랜드 매핑 수행
        
        Args:
            input_value: 원본 브랜드명 (예: "나이키", "NIKE", "nike")
            
        Returns:
            표준 브랜드명 또는 None (매칭 실패시)
        """
        if not input_value:
            return None
        
        # 입력값을 대문자로 변환하여 캐시에서 조회
        value = input_value.strip().upper()
        result = self.brand_cache.get(value)
        
        # 성능 통계 업데이트
        if result:
            self.stats['cache_hits'] += 1
        else:
            self.stats['cache_misses'] += 1
        
        return result
    
    def match_category_cached(self, cache_dict: Dict, input_value: str) -> Optional[str]:
        """
        캐시된 카테고리 매핑 수행
        
        Args:
            cache_dict: 사용할 카테고리 캐시 (category1_cache, category2_cache 등)
            input_value: 원본 카테고리명
            
        Returns:
            표준 카테고리명 또는 None (매칭 실패시)
        """
        if not input_value:
            return None
        
        value = input_value.strip().upper()
        result = cache_dict.get(value)
        
        # 성능 통계 업데이트
        if result:
            self.stats['cache_hits'] += 1
        else:
            self.stats['cache_misses'] += 1
        
        return result
    
    def match_country_cached(self, input_value: str) -> Optional[str]:
        """
        캐시된 국가 매핑 수행
        
        Args:
            input_value: 원본 국가명 (예: "한국", "korea", "KR")
            
        Returns:
            표준 국가명 또는 None (매칭 실패시)
        """
        if not input_value:
            return None
        
        value = input_value.strip().upper()
        result = self.country_cache.get(value)
        
        # 성능 통계 업데이트
        if result:
            self.stats['cache_hits'] += 1
        else:
            self.stats['cache_misses'] += 1
        
        return result
    
    # 단일 상품 변환
    def convert_single_product(self, raw_product):
        return self.bulk_convert_ultra_optimized(
            queryset=RawProduct.objects.filter(pk=raw_product.pk),
            batch_size=1
        )[0] == 1
    
    def bulk_convert_ultra_optimized(self, queryset, batch_size: int = 500) -> Tuple[int, int]:
        """
        대폭 최적화된 대량 상품 변환
        
        주요 최적화 사항:
        1. 기존 데이터 미리 로드하여 메모리에 캐싱
        2. 배치 단위 처리로 메모리 효율성 확보
        3. bulk_create/bulk_update로 DB 성능 최적화
        4. 단일 트랜잭션으로 데이터 일관성 보장
        5. 단순화된 로깅으로 가독성 향상
        
        Args:
            queryset: 변환할 RawProduct 쿼리셋
            batch_size: 배치 크기 (기본 500개)
            
        Returns:
            (성공 개수, 실패 개수) 튜플
        """
        self.stats['start_time'] = time.time()
        
        # ========== 1단계: 기존 데이터 메모리 로드 ==========
        # 기존 Product와 ProductOption을 미리 메모리에 로드하여
        # 변환 중 매번 DB 조회하는 것을 방지
        existing_products = {}      # {external_product_id: Product 객체}
        existing_options = {}       # {(external_product_id, option_name): ProductOption 객체}
        
        # 모든 기존 상품을 메모리에 로드 (iterator로 메모리 효율성 확보)
        for product in Product.objects.all().iterator(chunk_size=1000):
            existing_products[product.external_product_id] = product
        
        # 모든 기존 옵션을 메모리에 로드
        for option in ProductOption.objects.select_related('product').iterator(chunk_size=2000):
            key = (option.product.external_product_id, option.option_name)
            existing_options[key] = option
        
        # ========== 2단계: 처리 대상 필터링 ==========
        # 재고가 있고 가격이 있는 상품만 처리 (성능 최적화)
        valid_queryset = queryset.filter(
            Q(options__stock__gt=0) & Q(price_org__gt=0)
        ).prefetch_related('options').distinct()
        
        total_count = valid_queryset.count()
        self.logger.info(f"📊 처리 대상: {total_count:,}개 상품 (재고 있는 것만)")
        
        # ========== 3단계: 배치 단위 처리 ==========
        # 메모리 효율성을 위해 일정 크기로 나누어 처리
        products_to_create = []     # 생성할 Product 객체들
        products_to_update = []     # 업데이트할 Product 객체들
        options_to_create = []      # 생성할 ProductOption 객체들
        options_to_update = []      # 업데이트할 ProductOption 객체들
        
        success_count = 0
        fail_count = 0
        processed_count = 0
        last_progress_report = 0    # 마지막 진행률 보고 시점
        
        # 각 배치별로 순차 처리
        for batch_start in range(0, total_count, batch_size):
            batch = valid_queryset[batch_start:batch_start + batch_size]
            
            # 배치 내 각 상품 처리
            for raw_product in batch:
                processed_count += 1
                self.stats['total_processed'] += 1
                
                # ========== 4단계: 기본 검증 ==========
                # 재고와 가격 유효성 검사
                total_stock = sum(opt.stock for opt in raw_product.options.all())
                if total_stock <= 0 or not raw_product.price_org or raw_product.price_org <= 0:
                    fail_count += 1
                    self.stats['fail_count'] += 1
                    continue
                
                # ========== 5단계: 매핑 수행 ==========
                # 캐시를 사용하여 빠른 매핑 처리
                std_brand = self.match_brand_cached(raw_product.raw_brand_name)
                std_cat1 = self.match_category_cached(self.category1_cache, raw_product.gender)
                std_cat2 = self.match_category_cached(self.category2_cache, raw_product.category1)
                std_cat3 = self.match_category_cached(self.category3_cache, raw_product.category2)
                
                # 국가 매핑 (빈 값 처리)
                origin_input = (raw_product.origin or "").strip()
                std_origin = self.match_country_cached(origin_input) if origin_input else "-"
                
                # 필수 매핑 실패시 스킵 (브랜드와 성별은 필수)
                if not std_brand or not std_cat1:
                    fail_count += 1
                    self.stats['fail_count'] += 1
                    continue
                
                # ========== 6단계: Product 처리 ==========
                external_id = raw_product.external_product_id
                
                # Product 데이터 준비
                product_data = {
                    'retailer': raw_product.retailer,
                    'season': raw_product.season,
                    'gender': std_cat1,
                    'category1': std_cat2,
                    'category2': std_cat3,
                    'image_url_1': raw_product.image_url_1,
                    'image_url_2': raw_product.image_url_2,
                    'image_url_3': raw_product.image_url_3,
                    'image_url_4': raw_product.image_url_4,
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
                
                # 기존 상품 여부에 따라 업데이트 또는 생성 준비
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
                
                # ========== 7단계: ProductOption 처리 ==========
                # 재고가 있는 옵션만 처리
                for raw_option in raw_product.options.filter(stock__gt=0):
                    option_key = (external_id, raw_option.option_name)
                    
                    option_data = {
                        'external_option_id': raw_option.external_option_id,
                        'stock': raw_option.stock,
                        'price': raw_option.price,
                        'option_url': raw_option.option_url or "",
                    }
                    
                    # 기존 옵션 여부에 따라 업데이트 또는 생성 준비
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
                
                success_count += 1
                self.stats['success_count'] += 1
            
            # ========== 8단계: DB 대량 처리 ==========
            # 배치가 완료되면 DB에 대량 저장 (트랜잭션으로 안전성 보장)
            if products_to_create or products_to_update or options_to_create or options_to_update:
                with transaction.atomic():
                    # Product 대량 생성
                    if products_to_create:
                        Product.objects.bulk_create(products_to_create, batch_size=200)
                        self.stats['bulk_creates'] += len(products_to_create)
                        products_to_create = []
                    
                    # Product 대량 업데이트
                    if products_to_update:
                        Product.objects.bulk_update(
                            products_to_update, 
                            ['season', 'gender', 'category1', 'category2', 'image_url_1',
                             'image_url_2', 'image_url_3', 'image_url_4', 'brand_name', 'product_name', 'sku', 'price_retail', 'price_org', 
                             'discount_rate', 'color', 'material', 'origin', 'status', 'updated_at'], 
                            batch_size=200
                        )
                        self.stats['bulk_updates'] += len(products_to_update)
                        products_to_update = []
                    
                    # ProductOption 대량 생성
                    if options_to_create:
                        ProductOption.objects.bulk_create(options_to_create, batch_size=500)
                        self.stats['bulk_creates'] += len(options_to_create)
                        options_to_create = []
                    
                    # ProductOption 대량 업데이트
                    if options_to_update:
                        ProductOption.objects.bulk_update(
                            options_to_update,
                            ['external_option_id', 'stock', 'price', 'option_url'],
                            batch_size=500
                        )
                        self.stats['bulk_updates'] += len(options_to_update)
                        options_to_update = []
                    
                    # RawProduct 상태 업데이트 (변환 완료 표시)
                    success_raw_ids = [rp.id for rp in batch if rp.external_product_id in existing_products]
                    if success_raw_ids:
                        RawProduct.objects.filter(id__in=success_raw_ids).update(
                            status='converted', 
                            updated_at=now()
                        )
            
            # ========== 9단계: 진행률 보고 (25% 단위) ==========
            # 불필요한 로깅을 줄이기 위해 25% 단위로만 진행률 보고
            progress = (processed_count / total_count) * 100
            
            # 25%씩 진행률 보고 (25%, 50%, 75%)
            current_quarter = int(progress // 25)
            if current_quarter > last_progress_report and current_quarter < 4:
                last_progress_report = current_quarter
                self.logger.info(f"🔄 변환 진행 중... ({current_quarter * 25}% 완료 - {processed_count:,}/{total_count:,})")
        
        return success_count, fail_count
    
    def print_performance_stats(self):
        """
        성능 통계 출력 (단순화된 형태)
        
        주요 지표만 간단히 표시:
        - 처리 결과 (성공/실패)
        - 소요 시간 및 처리 속도
        - DB 작업 통계 (생성/업데이트)
        """
        elapsed = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        
        self.logger.info("✅ 변환 완료")
        
        # 처리 결과 요약
        if self.stats['total_processed'] > 0:
            success_rate = (self.stats['success_count'] / self.stats['total_processed']) * 100
            self.logger.info(f"📊 결과: 성공 {self.stats['success_count']:,}개 / 실패 {self.stats['fail_count']:,}개 ({success_rate:.1f}% 성공률)")

        # 성능 지표
        if elapsed > 0:
            rate = self.stats['total_processed'] / elapsed
            self.logger.info(f"⏱️ 소요시간: {elapsed:.1f}초 ({rate:.1f}개/초)")

        # DB 작업 통계
        self.logger.info(f"🔥 DB 작업: 생성 {self.stats['bulk_creates']:,}개 / 업데이트 {self.stats['bulk_updates']:,}개")







# ========== 호환성 유지를 위한 기존 클래스 ==========
class OptimizedConversionService(UltraOptimizedConversionService):
    """기존 OptimizedConversionService 호환성 유지"""
    def bulk_convert_optimized(self, queryset, batch_size: int = 2000) -> Tuple[int, int]:
        return self.bulk_convert_ultra_optimized(queryset, batch_size)


# ========== 싱글톤 패턴으로 서비스 인스턴스 관리 ==========
_conversion_service = None

def get_conversion_service(logger=None):
    """
    변환 서비스 인스턴스 반환 (싱글톤 패턴)
    
    매핑 캐시를 재사용하기 위해 싱글톤으로 관리
    """
    global _conversion_service
    if _conversion_service is None:
        _conversion_service = UltraOptimizedConversionService(logger=logger)
    return _conversion_service


# ========== 거래처별 대량 변환 함수 ==========
def bulk_convert_or_update_products_by_retailer(retailer_code, batch_size=500):
    """
    특정 거래처의 상품들을 대량 변환
    
    Args:
        retailer_code: 거래처 코드 (예: "NIKE", "ADIDAS")
        batch_size: 배치 크기
        
    Returns:
        성공한 변환 개수
    """
    # 거래처별 전용 로거 생성
    retailer_logger = get_product_logger(retailer_code)
    service = get_conversion_service(logger=retailer_logger)

    retailer_logger.info(f"🚀 [{retailer_code}] 대량 변환 시작...")

    # 해당 거래처의 미처리/처리된 상품들 조회
    raw_products = RawProduct.objects.filter(
        retailer=retailer_code,
        status__in=['pending', 'converted']
    )
    
    # 대량 변환 실행
    success_count, fail_count = service.bulk_convert_ultra_optimized(raw_products, batch_size)
    
    # 성능 통계 출력
    service.print_performance_stats()
    retailer_logger.info(f"✅ [{retailer_code}] 전송 완료 - 성공: {success_count:,}개 / 실패: {fail_count:,}개")
    
    return success_count


# ========== 솔드아웃 동기화 함수 ==========
def sync_soldout_products_from_raw(retailer_code: str):
    """
    원본 상품이 솔드아웃된 경우 가공 상품도 솔드아웃 처리
    
    Args:
        retailer_code: 거래처 코드
    """
    retailer_logger = get_product_logger(retailer_code)

    # 원본에서 솔드아웃된 상품 ID들 조회
    soldout_ids = RawProduct.objects.filter(
        retailer=retailer_code,
        status="soldout"
    ).values_list("external_product_id", flat=True)

    # 해당 상품들을 가공 테이블에서도 솔드아웃 처리
    updated_count = Product.objects.filter(
        retailer=retailer_code,
        external_product_id__in=soldout_ids
    ).update(status="soldout")

    retailer_logger.info(f"🔁 가공상품 soldout 처리 완료: {updated_count:,}개")


# ========== 기존 함수들 (호환성 유지) ==========
def convert_or_update_product(raw_product):
    """
    단일 상품 변환 (기존 인터페이스 유지)
    
    Args:
        raw_product: 변환할 RawProduct 객체
    """
    service = get_conversion_service()
    # 단일 상품 변환 로직은 기존과 동일
    return service.convert_single_product(raw_product)



def bulk_convert_or_update_products(batch_size=500):
    """
    전체 상품 대량 변환 (기존 인터페이스 유지)
    
    Args:
        batch_size: 배치 크기
        
    Returns:
        성공한 변환 개수
    """
    service = get_conversion_service()
    
    logger.info("🚀 전체 대량 변환 시작...")
    
    # 모든 미처리/처리된 상품들 조회
    raw_products = RawProduct.objects.filter(
        status__in=['pending', 'converted']
    )
    
    # 대량 변환 실행
    success_count, fail_count = service.bulk_convert_ultra_optimized(raw_products, batch_size)
    
    # 성능 통계 출력
    service.print_performance_stats()
    logger.info(f"✅ 전체 전송 완료 - 성공: {success_count:,}개 / 실패: {fail_count:,}개")
    
    return success_count