# shop/services/product/conversion_service.py

from shop.models import RawProduct, Product, RawProductOption, ProductOption
from django.db import transaction
from django.utils.timezone import now
from django.db.models import Q
from dictionary.models import BrandAlias, CategoryLevel1Alias, CategoryLevel2Alias, CategoryLevel3Alias
from pricing.models import CountryAlias
from shop.services.price_calculator import calculate_final_price, calculate_retail_price, calculate_option_final_price
from shop.utils.markup_util import get_markup_from_product
from decimal import Decimal
from eventlog.services.log_service import log_conversion_failure
import logging
import time

logger = logging.getLogger(__name__)


class UltraOptimizedConversionService:
    """최종 최적화된 상품 변환 서비스"""


 #===========================
    def _build_reason_from_raw(self, raw_product):
        """
        원본(raw) 값과 현재 캐시 매칭 결과를 사용해
        '브랜드 성공 / 카테고리 실패(사유: ...) / 원산지 성공' 형식의 문자열을 생성.
        반환: (reason_str, all_ok_bool)
        """
        # 원본값 정리
        brand_src = (getattr(raw_product, "raw_brand_name", "") or "").strip()
        gender_src = (getattr(raw_product, "gender", "") or "").strip()
        c1_src    = (getattr(raw_product, "category1", "") or "").strip()
        c2_src    = (getattr(raw_product, "category2", "") or "").strip()
        origin_src= (getattr(raw_product, "origin", "") or "").strip()

        # 캐시 매칭 (이미 있는 캐시/유틸 사용)
        brand_ok   = bool(self._match_cached(self.brand_cache,    brand_src))
        gender_ok  = bool(self._match_cached(self.category1_cache, gender_src))
        c1_ok      = bool(self._match_cached(self.category2_cache, c1_src)) if c1_src else True
        c2_ok      = bool(self._match_cached(self.category3_cache, c2_src)) if c2_src else True
        origin_ok  = bool(self._match_cached(self.country_cache,   origin_src))
        category_ok = (gender_ok and c1_ok and c2_ok)

        parts = []
        parts.append("브랜드 성공" if brand_ok else f"브랜드 실패(사유: '{brand_src}' 미매핑)")
        if category_ok:
            parts.append("카테고리 성공")
        else:
            parts.append(f'카테고리 실패(사유: gender="{gender_src}" category1="{c1_src}" category2="{c2_src}" 미매핑)')
        parts.append("원산지 성공" if origin_ok else f"원산지 실패(사유: {origin_src or '값 없음'})")
    
        return " / ".join(parts), (brand_ok and category_ok and origin_ok)

# ==========================
    
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
        
        # 카테고리 매핑 (소분류)        
        for alias in CategoryLevel3Alias.objects.select_related('category').all():
            for name in alias.alias.split(","):
                self.category3_cache[name.strip().upper()] = alias.category.name
        
        # 국가 매핑
        for alias in CountryAlias.objects.select_related('standard_country').all():
            for name in alias.origin_name.split(","):
                self.country_cache[name.strip().upper()] = alias.standard_country.name
        
        elapsed = time.time() - start_time
        logger.info(f"매핑 캐시 로딩 완료 ({elapsed:.1f}초)")

    def _match_cached(self, cache_dict, input_value):
        """캐시에서 매핑 조회"""
        if not input_value:
            return None
        return cache_dict.get(input_value.strip().upper())

    # ✅ 새로운 단일상품 변환 메서드 (경량화)
    def convert_single_product_lightweight(self, raw_product):
        """단일상품 경량화 변환 - 전체 데이터 로드 없이 해당 상품만 처리"""
        start_time = time.time()
        logger.info(f"단일상품 변환 시작: [{raw_product.retailer}-{raw_product.external_product_id}]")
        
        try:
            # 1) 기본 검증
            if not self._validate_raw_product(raw_product):
                # ✅ 검증 실패 → 단계별 포맷으로 로그
                reason, _ = self._build_reason_from_raw(raw_product)
                log_conversion_failure(raw_product, reason, source="conversion")
                logger.warning(f"검증 실패: [{raw_product.retailer}-{raw_product.external_product_id}]")
                return False

            # 2) 매핑 수행
            mapped_data = self._perform_mapping(raw_product)
            if not mapped_data:
                # ✅ 매핑 실패 → 단계별 포맷으로 로그
                reason, _ = self._build_reason_from_raw(raw_product)
                log_conversion_failure(raw_product, reason, source="conversion")
                logger.warning(f"매핑 실패: [{raw_product.retailer}-{raw_product.external_product_id}]")
                return False

            # 3) 가격 계산
            price_data = self._calculate_prices_with_external_functions(raw_product, mapped_data)

            # 4) 기존 상품 조회
            existing_product = Product.objects.filter(
                retailer=raw_product.retailer,
                external_product_id=raw_product.external_product_id
            ).first()

            # 5) 저장 데이터 구성
            product_data = self._build_product_data(raw_product, mapped_data, price_data)

            with transaction.atomic():
                if existing_product:
                    for key, value in product_data.items():
                        setattr(existing_product, key, value)
                    existing_product.save()
                    product = existing_product
                    logger.info(f"상품 업데이트 완료: [{raw_product.retailer}-{raw_product.external_product_id}]")
                else:
                    product = Product.objects.create(
                        external_product_id=raw_product.external_product_id,
                        created_at=raw_product.created_at or now(),
                        **product_data
                    )
                    logger.info(f"상품 생성 완료: [{raw_product.retailer}-{raw_product.external_product_id}]")

            # 옵션 처리 (기존 로직 유지)
            self._process_single_product_options(raw_product, product)

            return True

        except Exception as e:
            # ✅ 예외 발생 → 단계별 포맷 + 에러 꼬리표로 로그
            base_reason, _ = self._build_reason_from_raw(raw_product)
            reason = f"{base_reason} / 저장 실패(에러: {type(e).__name__}: {e})"
            log_conversion_failure(raw_product, reason, source="conversion")
            logger.exception(f"예외로 인한 변환 실패: [{raw_product.retailer}-{raw_product.external_product_id}] - {e}")
            return False



    # ✅ 단일상품용 옵션 처리 메서드 (경량화)
    def _process_single_product_options(self, raw_product, product):
        """단일상품의 옵션만 처리 - 전체 옵션 데이터 로드 없음"""
        
        # 해당 상품의 기존 옵션만 조회 (핵심 최적화!)
        existing_options = {
            opt.option_name: opt 
            for opt in ProductOption.objects.filter(product=product)
        }
        
        # 재고가 있는 원본 옵션만 처리
        for raw_option in raw_product.options.filter(stock__gt=0):
            # 옵션 가격 계산
            option_price_krw = None
            if raw_option.price:
                temp_option = type('TempOption', (), {
                    'price': raw_option.price,
                    'product': type('TempProduct', (), {
                        'category1': product.category1,
                        'origin': product.origin,
                        'retailer': product.retailer
                    })()
                })()
                option_price_krw = calculate_option_final_price(temp_option)
            
            option_data = {
                'external_option_id': raw_option.external_option_id,
                'stock': raw_option.stock,
                'price': raw_option.price,
                'price_krw': option_price_krw,
                'option_url': raw_option.option_url or "",
            }
            
            # 기존 옵션 확인
            if raw_option.option_name in existing_options:
                # 기존 옵션 업데이트
                existing_option = existing_options[raw_option.option_name]
                for key, value in option_data.items():
                    setattr(existing_option, key, value)
                existing_option.save()
                logger.debug(f"옵션 업데이트: {raw_option.option_name}")
            else:
                # 새 옵션 생성
                ProductOption.objects.create(
                    product=product,
                    option_name=raw_option.option_name,
                    **option_data
                )
                logger.debug(f"옵션 생성: {raw_option.option_name}")

    def bulk_convert_optimized(self, queryset, batch_size=500):
        """최종 최적화된 대량 변환 (bulk 연산 적용)"""
        start_time = time.time()
        
        # ✅ 수정: 거래처별로 기존 데이터 미리 로드 (거래처 + 상품ID 조합으로 캐싱)
        existing_products = {(p.retailer, p.external_product_id): p
                           for p in Product.objects.all().iterator(chunk_size=1000)}
        existing_options = {(opt.product.retailer, opt.product.external_product_id, opt.option_name): opt
                          for opt in ProductOption.objects.select_related('product').iterator(chunk_size=2000)}
        
        # 처리 대상 필터링 (재고 있는 것만)
        valid_queryset = queryset.filter(
            Q(options__stock__gt=0) & Q(price_org__gt=0)
        ).prefetch_related('options').distinct()
        
        total_count = valid_queryset.count()
        logger.info(f"변환 시작: {total_count:,}개 상품")
        
        # 배치 단위 처리
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
                mapped_data = self._perform_mapping(raw_product)
                if not mapped_data:
                    self.stats['failed'] += 1
                    continue
                
                # 가격 계산 (다른 파일의 함수들 호출)
                price_data = self._calculate_prices_with_external_functions(raw_product, mapped_data)
                
                # ✅ 수정: Product 처리 - 거래처와 상품ID 조합으로 기존 상품 찾기
                product_key = (raw_product.retailer, raw_product.external_product_id)
                product_data = self._build_product_data(raw_product, mapped_data, price_data)
                
                if product_key in existing_products:
                    # 기존 상품 업데이트
                    existing_product = existing_products[product_key]
                    for key, value in product_data.items():
                        setattr(existing_product, key, value)
                    products_to_update.append(existing_product)
                else:
                    # 새 상품 생성
                    new_product = Product(
                        external_product_id=raw_product.external_product_id,
                        created_at=raw_product.created_at or now(),
                        **product_data
                    )
                    products_to_create.append(new_product)
                    existing_products[product_key] = new_product
                
                # ✅ 수정: ProductOption 처리 - 거래처 정보 포함
                self._process_options_with_external_functions(
                    raw_product, existing_products[product_key], 
                    existing_options, options_to_create, options_to_update
                )
                
                self.stats['success'] += 1
                
            except Exception as e:
                logger.error(f"상품 처리 실패 [{raw_product.retailer}-{raw_product.external_product_id}]: {str(e)}")
                self.stats['failed'] += 1
        
        # bulk 연산으로 DB 저장
        self._bulk_save_batch(products_to_create, products_to_update, 
                             options_to_create, options_to_update, batch)

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
        
        # 필수 매핑 검증
        if not std_brand or not std_gender:
            return None
            
        return {
            'brand': std_brand,
            'gender': std_gender,
            'category1': std_category1 or "-",
            'category2': std_category2 or "-",
            'origin': std_origin
        }

    def _calculate_prices_with_external_functions(self, raw_product, mapped_data):
        """외부 함수들을 활용한 가격 계산"""
        # 1. 마크업 계산 (markup_util.py의 최적화된 함수 사용)
        markup = get_markup_from_product(raw_product) or 1.0
        
        # 2. 공급가 계산
        price_supply = raw_product.price_org * Decimal(str(markup))
        
        # 3. 임시 Product 객체 생성 (가격 계산용)
        temp_product = type('TempProduct', (), {
            'price_supply': price_supply,
            'price_retail': raw_product.price_retail,
            'category1': mapped_data['category1'],
            'origin': mapped_data['origin'],
            'retailer': raw_product.retailer
        })()
        
        # 4. 원화가 계산 (price_calculator.py의 최적화된 함수 사용)
        calculated_price_krw = calculate_final_price(temp_product)
        
        # 5. 소비자가 계산 (price_calculator.py의 최적화된 함수 사용)
        retail_price_krw = calculate_retail_price(temp_product)
        
        return {
            'markup': markup,
            'price_supply': price_supply,
            'calculated_price_krw': calculated_price_krw,
            'retail_price_krw': retail_price_krw
        }

    def _build_product_data(self, raw_product, mapped_data, price_data):
        """Product 저장용 데이터 구성"""
        return {
            'retailer': raw_product.retailer,
            'season': raw_product.season,
            'gender': mapped_data['gender'],
            'category1': mapped_data['category1'],
            'category2': mapped_data['category2'],
            'image_url_1': raw_product.image_url_1,
            'image_url_2': raw_product.image_url_2,
            'image_url_3': raw_product.image_url_3,
            'image_url_4': raw_product.image_url_4,
            'raw_brand_name': raw_product.raw_brand_name,
            'brand_name': mapped_data['brand'],
            'product_name': raw_product.product_name,
            'sku': raw_product.sku,
            'price_org': raw_product.price_org,
            'markup': price_data['markup'],
            'price_supply': price_data['price_supply'],
            'calculated_price_krw': price_data['calculated_price_krw'],
            'retail_price_krw': price_data['retail_price_krw'],
            'price_retail': raw_product.price_retail,
            'discount_rate': raw_product.discount_rate or 0,
            'color': raw_product.color,
            'material': raw_product.material,
            'origin': mapped_data['origin'],
            'status': 'active',
            'updated_at': now(),
        }

    def _process_options_with_external_functions(self, raw_product, product, existing_options, 
                                               options_to_create, options_to_update):
        """✅ 수정: 외부 함수를 활용한 옵션 처리 - 거래처 정보 포함"""
        for raw_option in raw_product.options.filter(stock__gt=0):
            # 거래처, 상품ID, 옵션명 조합으로 기존 옵션 찾기
            option_key = (raw_product.retailer, raw_product.external_product_id, raw_option.option_name)
            
            # 옵션 가격 계산 (price_calculator.py의 최적화된 함수 사용)
            option_price_krw = None
            if raw_option.price:
                # 임시 옵션 객체 생성
                temp_option = type('TempOption', (), {
                    'price': raw_option.price,
                    'product': type('TempProduct', (), {
                        'category1': product.category1,
                        'origin': product.origin,
                        'retailer': product.retailer
                    })()
                })()
                option_price_krw = calculate_option_final_price(temp_option)
            
            option_data = {
                'external_option_id': raw_option.external_option_id,
                'stock': raw_option.stock,
                'price': raw_option.price,
                'price_krw': option_price_krw,
                'option_url': raw_option.option_url or "",
            }
            
            if option_key in existing_options:
                # 기존 옵션 업데이트
                existing_option = existing_options[option_key]
                for key, value in option_data.items():
                    setattr(existing_option, key, value)
                options_to_update.append(existing_option)
            else:
                # 새 옵션 생성
                new_option = ProductOption(
                    product=product,
                    option_name=raw_option.option_name,
                    **option_data
                )
                options_to_create.append(new_option)
                existing_options[option_key] = new_option

    def _bulk_save_batch(self, products_to_create, products_to_update, 
                        options_to_create, options_to_update, raw_batch):
        """bulk 연산으로 배치 저장"""
        with transaction.atomic():
            # Product bulk 생성
            if products_to_create:
                Product.objects.bulk_create(products_to_create, batch_size=200)
            
            # Product bulk 업데이트
            if products_to_update:
                Product.objects.bulk_update(
                    products_to_update,
                    ['season', 'gender', 'category1', 'category2', 'image_url_1', 
                     'image_url_2', 'image_url_3', 'image_url_4', 'brand_name', 
                     'product_name', 'sku', 'price_org', 'markup', 'price_supply',
                     'calculated_price_krw', 'retail_price_krw', 'price_retail',
                     'discount_rate', 'color', 'material', 'origin', 'status', 'updated_at'],
                    batch_size=200
                )
            
            # ProductOption bulk 생성
            if options_to_create:
                ProductOption.objects.bulk_create(options_to_create, batch_size=500)
            
            # ProductOption bulk 업데이트
            if options_to_update:
                ProductOption.objects.bulk_update(
                    options_to_update,
                    ['external_option_id', 'stock', 'price', 'price_krw', 'option_url'],
                    batch_size=500
                )
            
            # RawProduct 상태 bulk 업데이트
            success_ids = [rp.id for rp in raw_batch]
            RawProduct.objects.filter(id__in=success_ids).update(
                status='converted', 
                updated_at=now()
            )

    # ✅ 기존 단일상품 변환 메서드 수정 (새로운 경량화 메서드 호출)
    def convert_single_product(self, raw_product):
        """단일 상품 변환 - 경량화 메서드 사용"""
        return self.convert_single_product_lightweight(raw_product)


# 싱글톤 패턴으로 서비스 인스턴스 관리
_conversion_service = None

def get_conversion_service():
    """
    변환 서비스 싱글톤 객체 반환
    """
    global _conversion_service
    if _conversion_service is None:
        _conversion_service = UltraOptimizedConversionService()
    return _conversion_service


# ✅ 캐시 강제 리로드 함수 추가
def reload_conversion_cache():
    """
    매핑 캐시를 강제로 다시 로딩한다.
    - BrandAlias, CategoryAlias, CountryAlias 등 최신 데이터 반영
    """
    global _conversion_service
    if _conversion_service is None:
        _conversion_service = UltraOptimizedConversionService()
        logger.info("[ConversionService] 매핑 캐시 새로 생성 및 로딩 완료")
    else:
        _conversion_service._load_mapping_caches()
        logger.info("[ConversionService] 매핑 캐시 강제 리로드 완료")
    return _conversion_service


# 거래처별 대량 변환
def bulk_convert_by_retailer(retailer_code, batch_size=500):
    """특정 거래처 상품 대량 변환"""
    service = get_conversion_service()
    logger.info(f"[{retailer_code}] 변환 시작")

    raw_products = RawProduct.objects.filter(
        retailer=retailer_code,
        status__in=['pending', 'converted']
    )
    
    success_count, fail_count = service.bulk_convert_optimized(raw_products, batch_size)
    logger.info(f"[{retailer_code}] 완료 - 성공: {success_count:,}개, 실패: {fail_count:,}개")
    
    return success_count


# 솔드아웃 동기화 (함수명 수정)
def sync_soldout_products_from_raw(retailer_code: str):
    """원본 솔드아웃 상품을 가공 테이블에 반영"""
    soldout_ids = RawProduct.objects.filter(
        retailer=retailer_code,
        status="soldout"
    ).values_list("external_product_id", flat=True)

    updated_count = Product.objects.filter(
        retailer=retailer_code,
        external_product_id__in=soldout_ids
    ).update(status="soldout")

    logger.info(f"[{retailer_code}] 솔드아웃 동기화: {updated_count:,}개")


# 기존 호환성 함수들
def convert_or_update_product(raw_product):
    """단일 상품 변환 (기존 호환성) - ✅ 새로운 경량화 메서드 사용"""
    service = get_conversion_service()
    return service.convert_single_product_lightweight(raw_product)

def bulk_convert_or_update_products(batch_size=500):
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