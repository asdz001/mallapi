# shop/services/conversion_service.py

from shop.models import RawProduct, Product, RawProductOption, ProductOption
from django.db import transaction
from django.utils.timezone import now
from django.db.models import Q
from dictionary.models import BrandAlias, CategoryLevel1Alias, CategoryLevel2Alias, CategoryLevel3Alias
from pricing.models import CountryAlias
from shop.services.price_calculator import calculate_final_price, calculate_retail_price, calculate_option_final_price
from shop.utils.markup_util import get_markup_from_product
from decimal import Decimal
import logging
import time

logger = logging.getLogger(__name__)

class UltraOptimizedConversionService:
    """최종 최적화된 상품 변환 서비스"""
    
    def __init__(self):
        # 매핑 데이터 캐시만 관리 (가격 계산은 다른 파일에서)
        self.brand_cache = {}
        self.category1_cache = {}
        self.category2_cache = {}
        self.category3_cache = {}
        self.country_cache = {}
        
        # 성능 통계
        self.stats = {'processed': 0, 'success': 0, 'failed': 0}
        
        # 매핑 데이터만 로드
        self._load_mapping_caches()
    
    def _load_mapping_caches(self):
        """매핑 데이터를 메모리에 캐시"""
        start_time = time.time()
        
        # 브랜드 매핑
        for alias in BrandAlias.objects.select_related('brand').all():
            for name in alias.alias.split(","):
                self.brand_cache[name.strip().upper()] = alias.brand.name
        
        # 카테고리 매핑 (성별)
        for alias in CategoryLevel1Alias.objects.select_related('category').all():
            for name in alias.alias.split(","):
                self.category1_cache[name.strip().upper()] = alias.category.name
        
        # 카테고리 매핑 (대분류)
        for alias in CategoryLevel2Alias.objects.select_related('category').all():
            for name in alias.alias.split(","):
                self.category2_cache[name.strip().upper()] = alias.category.name
        
        # 카테고리 매핑 (중분류)
        for alias in CategoryLevel3Alias.objects.select_related('category').all():
            for name in alias.alias.split(","):
                self.category3_cache[name.strip().upper()] = alias.category.name
        
        # 원산지 매핑
        for alias in CountryAlias.objects.select_related('country').all():
            for name in alias.alias.split(","):
                self.country_cache[name.strip().upper()] = alias.country.name
        
        elapsed = time.time() - start_time
        logger.info(f"매핑 캐시 로딩 완료 ({elapsed:.1f}초)")

    def _match_cached(self, cache_dict, input_value):
        """캐시에서 매핑 조회"""
        if not input_value:
            return None
        return cache_dict.get(input_value.strip().upper())

    def bulk_convert_optimized(self, queryset, batch_size=500):
        """최종 최적화된 대량 변환 (bulk 연산 적용)"""
        start_time = time.time()
        
        # ✅ 수정: 거래처별로 기존 데이터 미리 로드 (거래처 + 상품ID 조합으로 캐싱)
        existing_products = {(p.retailer, p.external_product_id): p
                             for p in Product.objects.only('id','retailer','external_product_id')}
        existing_options = {(o.product_id, o.external_option_id): o
                            for o in ProductOption.objects.only('id','product_id','external_option_id')}
        
        valid_queryset = queryset.select_related('retailer').prefetch_related('options')
        total_count = valid_queryset.count()
        logger.info(f"최적화된 변환 시작: 대상 {total_count:,}개")
        
        for batch_start in range(0, total_count, batch_size):
            batch = valid_queryset[batch_start:batch_start + batch_size]
            self._process_batch_optimized(batch, existing_products, existing_options)
            
            # 25% 단위 진행률 로그
            progress = ((batch_start + batch_size) / total_count) * 100
            if progress % 25 < (batch_size / total_count) * 100:
                logger.info(f"진행률: {min(100, int(progress))}%")
        
        elapsed = time.time() - start_time
        logger.info(f"변환 완료: 성공 {self.stats['success']:,}개, "
                   f"실패 {self.stats['failed']:,}개 ({elapsed:.1f}초)")
        
        return self.stats['success'], self.stats['failed']

    def _process_batch_optimized(self, batch, existing_products, existing_options):
        """최적화된 배치 처리"""
        products_to_create = []
        products_to_update = []
        options_to_create = []
        options_to_update = []
        
        for raw_product in batch:
            try:
                # 기본 검증
                if not self._validate_raw_product(raw_product):
                    self.stats['failed'] += 1
                    continue
                
                # 매핑 수행
                mapped = self._perform_mapping(raw_product)
                if not mapped:
                    self.stats['failed'] += 1
                    continue
                
                # 기존 Product 존재 여부 확인 (retailer + external_product_id 기준)
                key = (raw_product.retailer, raw_product.external_product_id)
                existing_product = existing_products.get(key)
                
                if existing_product:
                    # 업데이트 대상
                    self._apply_product_fields(existing_product, raw_product, mapped)
                    products_to_update.append(existing_product)
                else:
                    # 생성 대상
                    new_product = self._build_product_instance(raw_product, mapped)
                    products_to_create.append(new_product)
                
                self.stats['success'] += 1
            
            except Exception as e:
                logger.exception(f"배치 처리 중 예외: raw_id={raw_product.id}, err={e}")
                self.stats['failed'] += 1
        
        # Product 일괄 처리
        with transaction.atomic():
            if products_to_create:
                Product.objects.bulk_create(products_to_create, batch_size=1000)
                # 방금 생성한 product들의 ID 재조회 필요
                created_keys = {(p.retailer, p.external_product_id) for p in products_to_create}
                for p in Product.objects.filter(
                    retailer__in=[k[0] for k in created_keys],
                    external_product_id__in=[k[1] for k in created_keys]
                ).only('id','retailer','external_product_id'):
                    existing_products[(p.retailer, p.external_product_id)] = p
            
            if products_to_update:
                Product.objects.bulk_update(
                    products_to_update,
                    fields=[
                        'brand','gender','category1','category2','origin',
                        'name','description','price_org','price_retail','price_final',
                        'discount_rate','currency','status','stock','updated_at'
                    ],
                    batch_size=1000
                )
        
        # 옵션 처리 (Product 생성 후 option 처리해야 함)
        for raw_product in batch:
            try:
                product = existing_products.get((raw_product.retailer, raw_product.external_product_id))
                if not product:
                    # 이 케이스는 거의 없지만 방어적으로 처리
                    logger.warning(f"옵션 처리용 product 미발견: retailer={raw_product.retailer_id}, ext={raw_product.external_product_id}")
                    continue
                
                for raw_opt in raw_product.options.all():
                    opt_key = (product.id, raw_opt.external_option_id)
                    existing_option = existing_options.get(opt_key)
                    
                    if existing_option:
                        # 업데이트
                        self._apply_option_fields(existing_option, product, raw_opt)
                        options_to_update.append(existing_option)
                    else:
                        # 생성
                        new_opt = self._build_option_instance(product, raw_opt)
                        options_to_create.append(new_opt)
            
            except Exception as e:
                logger.exception(f"옵션 처리 중 예외: raw_id={raw_product.id}, err={e}")
                self.stats['failed'] += 1
        
        with transaction.atomic():
            if options_to_create:
                ProductOption.objects.bulk_create(options_to_create, batch_size=1000)
                for o in options_to_create:
                    existing_options[(o.product_id, o.external_option_id)] = o
            if options_to_update:
                ProductOption.objects.bulk_update(
                    options_to_update,
                    fields=['size','color','stock','price_final','status','updated_at'],
                    batch_size=1000
                )

    def _validate_raw_product(self, raw_product):
        """기본 검증"""
        total_stock = sum(opt.stock for opt in raw_product.options.all())
        return (total_stock > 0 and 
                raw_product.price_org and 
                raw_product.price_org > 0 and
                raw_product.raw_brand_name)

    def _perform_mapping(self, raw_product):
        """브랜드, 카테고리, 국가 매핑 (캐시 활용)"""
        std_brand = self._match_cached(self.brand_cache, raw_product.raw_brand_name)
        std_gender = self._match_cached(self.category1_cache, raw_product.gender)
        std_category1 = self._match_cached(self.category2_cache, raw_product.category1)
        std_category2 = self._match_cached(self.category3_cache, raw_product.category2)
        std_origin = self._match_cached(self.country_cache, raw_product.origin) or raw_product.origin or "-"
        
        if not std_brand or not std_gender or not std_category1:
            logger.debug(f"매핑 실패 - brand={raw_product.raw_brand_name}, "
                         f"gender={raw_product.gender}, cat1={raw_product.category1}")
            return None
        
        return {
            'brand': std_brand,
            'gender': std_gender,
            'category1': std_category1,
            'category2': std_category2,
            'origin': std_origin
        }

    def _apply_product_fields(self, product, raw, mapped):
        """기존 Product에 필드 적용"""
        product.brand = mapped['brand']
        product.gender = mapped['gender']
        product.category1 = mapped['category1']
        product.category2 = mapped['category2']
        product.origin = mapped['origin']
        
        product.name = raw.name
        product.description = raw.description
        product.currency = raw.currency or 'EUR'
        product.status = 'active'
        product.updated_at = now()
        
        # 가격 계산
        markup = get_markup_from_product(product)
        product.price_retail = calculate_retail_price(raw.price_org, markup)
        product.price_final = calculate_final_price(product.price_retail, raw.discount_rate or Decimal('0'))

        # 옵션 재고 합계 반영
        product.stock = sum(o.stock for o in raw.options.all())
    
    def _build_product_instance(self, raw, mapped):
        """새 Product 인스턴스 생성"""
        markup = get_markup_from_product(raw)  # Raw 기반으로도 마진 룰 가능
        price_retail = calculate_retail_price(raw.price_org, markup)
        price_final = calculate_final_price(price_retail, raw.discount_rate or Decimal('0'))
        
        return Product(
            retailer=raw.retailer,
            external_product_id=raw.external_product_id,
            brand=mapped['brand'],
            gender=mapped['gender'],
            category1=mapped['category1'],
            category2=mapped['category2'],
            origin=mapped['origin'],
            name=raw.name,
            description=raw.description,
            price_org=raw.price_org,
            price_retail=price_retail,
            price_final=price_final,
            discount_rate=raw.discount_rate or Decimal('0'),
            currency=raw.currency or 'EUR',
            status='active',
            stock=sum(o.stock for o in raw.options.all()),
            created_at=now(),
            updated_at=now(),
        )

    def _apply_option_fields(self, option, product, raw_opt):
        """기존 옵션에 필드 적용"""
        option.size = raw_opt.size
        option.color = raw_opt.color
        option.stock = raw_opt.stock
        option.status = 'active' if raw_opt.stock > 0 else 'soldout'
        option.updated_at = now()
        
        # 옵션 개별 가격 계산
        option.price_final = calculate_option_final_price(
            base_price=product.price_final,
            size=raw_opt.size,
            color=raw_opt.color
        )

    def _build_option_instance(self, product, raw_opt):
        """새 옵션 인스턴스 생성"""
        return ProductOption(
            product=product,
            external_option_id=raw_opt.external_option_id,
            size=raw_opt.size,
            color=raw_opt.color,
            stock=raw_opt.stock,
            status='active' if raw_opt.stock > 0 else 'soldout',
            price_final=calculate_option_final_price(
                base_price=product.price_final,
                size=raw_opt.size,
                color=raw_opt.color
            ),
            created_at=now(),
            updated_at=now(),
        )

# ---- 호환성을 위한 외부 진입 함수들 ----

def get_conversion_service():
    """서비스 인스턴스 제공 (싱글톤처럼 재사용 가능)"""
    # 간단히 매 호출시 생성해도 캐시 로딩이 가볍도록 설계했음
    return UltraOptimizedConversionService()

def convert_single_raw_product(raw_product_id):
    """단일 상품 변환 (기존 호환성)"""
    service = get_conversion_service()
    try:
        raw = RawProduct.objects.select_related('retailer').prefetch_related('options').get(id=raw_product_id)
    except RawProduct.DoesNotExist:
        logger.error(f"RawProduct 미존재: id={raw_product_id}")
        return False
    
    success, fail = service.bulk_convert_optimized(RawProduct.objects.filter(id=raw.id), batch_size=1)
    return success == 1 and fail == 0

def bulk_convert_by_retailer(retailer_code, batch_size=500):
    """거래처별 대량 변환 (기존 호환성)"""
    service = get_conversion_service()
    
    raw_products = RawProduct.objects.select_related('retailer').prefetch_related('options').filter(
        retailer__code=retailer_code,
        status__in=['pending', 'converted']
    )
    
    success_count, fail_count = service.bulk_convert_optimized(raw_products, batch_size)
    logger.info(f"[{retailer_code}] 변환 완료 - 성공: {success_count:,}개, 실패: {fail_count:,}개")
    
    return success_count

def bulk_convert_all_products(batch_size=500):
    """전체 상품 대량 변환 (기존 호환성)"""
    service = get_conversion_service()
    
    raw_products = RawProduct.objects.filter(
        status__in=['pending', 'converted']
    )
    
    success_count, fail_count = service.bulk_convert_optimized(raw_products, batch_size)
    logger.info(f"전체 변환 완료 - 성공: {success_count:,}개, 실패: {fail_count:,}개")
    
    return success_count

def bulk_convert_or_update_products_by_retailer(retailer_code, batch_size=500):
    """거래처별 대량 변환 (기존 호환성)"""
    return bulk_convert_by_retailer(retailer_code, batch_size)
