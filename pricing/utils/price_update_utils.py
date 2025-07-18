# pricing/utils/optimized_price_update_utils.py - 로거 분리 적용

from shop.models import Product
from pricing.models import BrandSetting, GlobalPricingSetting, FixedCountry, Retailer, CountryAlias, PriceFormulaRange
from django.db import transaction
from decimal import Decimal, ROUND_CEILING
from datetime import datetime

# ✅ 분리된 로거 import
from utils.bulk_update_logger import (
    get_bulk_update_logger, 
    log_start_session, 
    log_end_session, 
    log_error_session, 
    log_progress
)

def update_all_products_pricing(user=None, label="전체상품업데이트"):
    """🚀 최적화된 방식: 한번에 불러오기 → 나눠서 계산 → 한번에 저장"""
    # ✅ 분리된 로거 사용
    logger = get_bulk_update_logger()
    start_time = datetime.now()
    
    # 시작 로그
    log_start_session(logger, user, label)
    
    try:
        # 1단계: 한번에 모든 상품 불러오기
        log_progress(logger, "전체 상품 데이터 로딩 중...")
        all_products = list(Product.objects.values(
            'id', 'retailer', 'raw_brand_name', 'gender', 
            'category1', 'category2', 'origin', 'price_org',
            'markup', 'calculated_price_krw', 'season'
        ))
        
        total_count = len(all_products)
        log_progress(logger, f"총 {total_count:,}개 상품 로딩 완료")
        
        # 캐시 데이터 로드
        log_progress(logger, "설정 데이터 캐시 중...")
        markup_cache = _load_markup_cache()
        price_cache = _load_price_cache()
        log_progress(logger, "캐시 완료")
        
        # 2단계: 나눠서 계산 (메모리 절약)
        log_progress(logger, "가격 계산 시작...")
        batch_size = 1000  # 계산용 배치
        all_updates = []
        
        batch_count = (total_count + batch_size - 1) // batch_size
        log_progress(logger, f"{batch_count}개 배치로 나누어 계산")
        
        for batch_idx in range(0, total_count, batch_size):
            batch_num = batch_idx // batch_size + 1
            batch_end = min(batch_idx + batch_size, total_count)
            
            log_progress(logger, f"배치 {batch_num}/{batch_count} 계산 중... ({batch_idx:,} ~ {batch_end:,})")
            
            batch_products = all_products[batch_idx:batch_end]
            batch_updates = []
            
            for product_dict in batch_products:
                try:
                    new_markup = _get_markup_bulk_dict(product_dict, markup_cache) or 1.0
                    new_price = _calculate_price_bulk_dict(product_dict, new_markup, price_cache) or 0
                    
                    current_markup = product_dict['markup'] or 0
                    current_price = float(product_dict['calculated_price_krw'] or 0)
                    
                    if (abs(current_markup - new_markup) > 0.001 or 
                        abs(current_price - new_price) > 0.5):
                        batch_updates.append({
                            'id': product_dict['id'],
                            'markup': new_markup,
                            'calculated_price_krw': new_price
                        })
                except:
                    continue
            
            all_updates.extend(batch_updates)
            log_progress(logger, f"배치 {batch_num}: {len(batch_updates)}개 변경 감지")
        
        log_progress(logger, f"계산 완료 - 총 {len(all_updates):,}개 상품 변경 필요")
        
        # 3단계: 나누어서 저장 (서버 과부하 방지)
        if all_updates:
            log_progress(logger, "벌크 저장 시작...")
            
            # 저장용 배치 크기 (작게!)
            save_batch_size = 500
            total_saved = 0
            save_batch_count = (len(all_updates) + save_batch_size - 1) // save_batch_size
            
            log_progress(logger, f"{save_batch_count}개 저장 배치로 나누어 처리")
            
            for save_idx in range(0, len(all_updates), save_batch_size):
                save_batch_num = save_idx // save_batch_size + 1
                save_end = min(save_idx + save_batch_size, len(all_updates))
                
                log_progress(logger, f"저장 배치 {save_batch_num}/{save_batch_count} 처리 중... ({save_idx:,} ~ {save_end:,})")
                
                # 배치별로 Product 객체 조회
                batch_updates = all_updates[save_idx:save_end]
                product_ids = [update['id'] for update in batch_updates]
                product_objects = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
                
                # 업데이트할 객체들 준비
                bulk_updates = []
                for update in batch_updates:
                    if update['id'] in product_objects:
                        product_obj = product_objects[update['id']]
                        product_obj.markup = update['markup']
                        product_obj.calculated_price_krw = update['calculated_price_krw']
                        bulk_updates.append(product_obj)
                
                # 작은 배치로 저장
                if bulk_updates:
                    try:
                        with transaction.atomic():
                            Product.objects.bulk_update(
                                bulk_updates, 
                                ['markup', 'calculated_price_krw'],
                                batch_size=100  # 더 작게
                            )
                        
                        total_saved += len(bulk_updates)
                        log_progress(logger, f"저장 배치 {save_batch_num}: {len(bulk_updates)}개 저장 완료")
                        
                    except Exception as save_error:
                        log_progress(logger, f"저장 배치 {save_batch_num} 실패: {str(save_error)}")
                        # 개별 저장으로 복구
                        for update in batch_updates:
                            try:
                                Product.objects.filter(id=update['id']).update(
                                    markup=update['markup'],
                                    calculated_price_krw=update['calculated_price_krw']
                                )
                                total_saved += 1
                            except:
                                continue
                        log_progress(logger, f"저장 배치 {save_batch_num}: 개별 저장으로 복구 완료")
                
                # 서버 부하 감소
                if save_batch_num % 5 == 0:
                    import time
                    time.sleep(0.1)
            
            log_progress(logger, f"벌크 저장 완료 - {total_saved:,}개 상품 업데이트")
        else:
            log_progress(logger, "변경할 상품이 없습니다")
        
        # 성공 완료 로그
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        log_end_session(logger, len(all_updates), total_time, success=True)
        
        return len(all_updates)
        
    except Exception as e:
        # 실패 로그
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        log_error_session(logger, str(e), total_time)
        return 0


def _load_markup_cache():
    """마크업 캐시"""
    cache = {'retailers': {}, 'brand_settings': {}}
    
    for retailer in Retailer.objects.all():
        cache['retailers'][retailer.code] = retailer
    
    for setting in BrandSetting.objects.filter(is_active=True).order_by('priority', 'id'):
        retailer_code = setting.retailer.code
        if retailer_code not in cache['brand_settings']:
            cache['brand_settings'][retailer_code] = []
        
        setting_data = {
            'id': setting.id,
            'brand_name': setting.brand_name,
            'seasons': setting.seasons,
            'priority': setting.priority,
            'markups': []
        }
        
        for markup in setting.markups.filter(is_active=True):
            setting_data['markups'].append({
                'gender': markup.gender,
                'category': markup.category,
                'markup': markup.markup,
                'is_active': markup.is_active
            })
        
        cache['brand_settings'][retailer_code].append(setting_data)
    
    return cache


def _load_price_cache():
    """가격 계산 캐시"""
    cache = {'retailers': {}, 'global_setting': None, 'country_aliases': {}, 'price_formula_ranges': []}
    
    for retailer in Retailer.objects.all():
        cache['retailers'][retailer.code] = retailer
    
    try:
        global_setting = GlobalPricingSetting.objects.first()
        if global_setting:
            cache['global_setting'] = {
                'exchange_rate': Decimal(str(global_setting.exchange_rate)),
                'shipping_fee': Decimal("1.0") + (Decimal(str(global_setting.shipping_fee)) / Decimal("100")),
                'vat': Decimal("1.0") + (Decimal(str(global_setting.VAT)) / Decimal("100")),
                'margin': Decimal("1.0") + (Decimal(str(global_setting.margin_rate)) / Decimal("100")),
                'special_tax_rate': Decimal(str(global_setting.special_tax_rate)) / Decimal("100")
            }
    except:
        pass
    
    if not cache['global_setting']:
        cache['global_setting'] = {
            'exchange_rate': Decimal("1300"),
            'shipping_fee': Decimal("1.10"),
            'vat': Decimal("1.10"),
            'margin': Decimal("1.20"),
            'special_tax_rate': Decimal("0.20")
        }
    
    for alias in CountryAlias.objects.select_related("standard_country").all():
        cache['country_aliases'][alias.origin_name] = {
            'fta_applicable': alias.standard_country.fta_applicable
        }
    
    for range_obj in PriceFormulaRange.objects.all():
        cache['price_formula_ranges'].append({
            'min_price': range_obj.min_price,
            'max_price': range_obj.max_price,
            'formula': range_obj.formula
        })
    
    return cache


def _get_markup_bulk_dict(product_dict, markup_cache):
    """마크업 계산"""
    retailer_code = product_dict['retailer']
    product_brand = product_dict['raw_brand_name']
    product_gender = product_dict['gender'] or '전체'
    product_category = product_dict['category1'] or '전체'
    product_season = product_dict['season'] or '전체'
    
    if retailer_code not in markup_cache['retailers'] or not product_brand:
        return None
    
    if retailer_code not in markup_cache['brand_settings']:
        return None
    
    for setting in markup_cache['brand_settings'][retailer_code]:
        # 브랜드 매칭
        if setting['brand_name'] != "전체" and setting['brand_name'] != product_brand:
            continue
        
        # 시즌 매칭
        if setting['seasons']:
            if "전체" not in setting['seasons']:
                setting_seasons = [s.strip() for s in setting['seasons'].split(',')]
                if product_season not in setting_seasons:
                    continue
        
        # 마크업 찾기
        for markup_detail in setting['markups']:
            if (markup_detail['gender'] in [product_gender, '전체'] and 
                markup_detail['category'] in [product_category, '전체'] and 
                markup_detail['is_active']):
                return markup_detail['markup']
    
    return None


def _calculate_price_bulk_dict(product_dict, markup, price_cache):
    """가격 계산"""
    price_org = product_dict['price_org'] or 0
    if price_org <= 0:
        return 0
    
    price_supply = Decimal(str(price_org)) * Decimal(str(markup))
    category1 = product_dict['category1']
    retailer_code = product_dict['retailer']
    origin = product_dict['origin']
    
    if retailer_code not in price_cache['retailers']:
        return None
    
    global_setting = price_cache['global_setting']
    exchange_rate = global_setting['exchange_rate']
    shipping_fee = global_setting['shipping_fee']
    vat = global_setting['vat']
    margin = global_setting['margin']
    special_tax_rate = global_setting['special_tax_rate']
    
    # 관세
    tariff = Decimal("1.00")
    if origin in price_cache['country_aliases']:
        if not price_cache['country_aliases'][origin]['fta_applicable']:
            if category1 in ["의류", "신발"]:
                tariff = Decimal("1.13")
            elif category1 in ["가방", "액세서리"]:
                tariff = Decimal("1.08")
    else:
        if category1 in ["의류", "신발"]:
            tariff = Decimal("1.13")
        elif category1 in ["가방", "액세서리"]:
            tariff = Decimal("1.08")
    
    base = price_supply * exchange_rate
    
    # 구간별 추가금액
    extra_fee = Decimal("0")
    try:
        for range_data in price_cache['price_formula_ranges']:
            if range_data['min_price'] <= base <= range_data['max_price']:
                formula = range_data['formula'].replace("가격", str(base))
                extra_fee = Decimal(str(eval(formula)))
                break
    except:
        pass
    
    # 최종 계산
    if base > Decimal("2000000"):
        taxable_base = base * shipping_fee
        special_tax = (base - Decimal("2000000")) * special_tax_rate
        result = (taxable_base + special_tax) * tariff * vat * margin + extra_fee
    else:
        result = (base * shipping_fee) * tariff * vat * margin + extra_fee
    
    rounded_result = (result / Decimal("1000")).to_integral_value(rounding=ROUND_CEILING) * Decimal("1000")
    return int(rounded_result)


def update_products_by_retailer(retailer_code, user=None):
    """거래처별 업데이트"""
    logger = get_bulk_update_logger()
    start_time = datetime.now()
    
    log_start_session(logger, user, f"거래처업데이트 ({retailer_code})")
    
    try:
        # 해당 거래처 상품만 한번에 불러오기
        products = list(Product.objects.filter(retailer=retailer_code).values(
            'id', 'retailer', 'raw_brand_name', 'gender', 
            'category1', 'category2', 'origin', 'price_org',
            'markup', 'calculated_price_krw', 'season'
        ))
        
        if not products:
            log_progress(logger, f"거래처 {retailer_code}: 상품 없음")
            log_end_session(logger, 0, (datetime.now() - start_time).total_seconds(), success=True)
            return 0
        
        log_progress(logger, f"거래처 {retailer_code}: {len(products)}개 상품 로딩 완료")
        
        # 캐시 로드
        markup_cache = _load_markup_cache()
        price_cache = _load_price_cache()
        
        # 계산
        updates = []
        for product_dict in products:
            try:
                new_markup = _get_markup_bulk_dict(product_dict, markup_cache) or 1.0
                new_price = _calculate_price_bulk_dict(product_dict, new_markup, price_cache) or 0
                
                current_markup = product_dict['markup'] or 0
                current_price = float(product_dict['calculated_price_krw'] or 0)
                
                if (abs(current_markup - new_markup) > 0.001 or 
                    abs(current_price - new_price) > 0.5):
                    updates.append({
                        'id': product_dict['id'],
                        'markup': new_markup,
                        'calculated_price_krw': new_price
                    })
            except:
                continue
        
        # 저장
        if updates:
            product_ids = [update['id'] for update in updates]
            product_objects = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
            
            bulk_updates = []
            for update in updates:
                if update['id'] in product_objects:
                    product_obj = product_objects[update['id']]
                    product_obj.markup = update['markup']
                    product_obj.calculated_price_krw = update['calculated_price_krw']
                    bulk_updates.append(product_obj)
            
            with transaction.atomic():
                Product.objects.bulk_update(bulk_updates, ['markup', 'calculated_price_krw'])
            
            log_progress(logger, f"거래처 {retailer_code}: {len(bulk_updates)}개 업데이트 완료")
        else:
            log_progress(logger, f"거래처 {retailer_code}: 변경사항 없음")
        
        # 완료 로그
        total_time = (datetime.now() - start_time).total_seconds()
        log_end_session(logger, len(updates), total_time, success=True)
        
        return len(updates)
        
    except Exception as e:
        total_time = (datetime.now() - start_time).total_seconds()
        log_error_session(logger, str(e), total_time)
        return 0


def update_products_by_brand_and_retailer(retailer_code, brand_name, user=None):
    """거래처+브랜드별 업데이트"""
    if brand_name in ['전체', 'ETC']:
        return update_products_by_retailer(retailer_code, user)
    
    logger = get_bulk_update_logger()
    start_time = datetime.now()
    
    log_start_session(logger, user, f"브랜드업데이트 ({retailer_code}-{brand_name})")
    
    try:
        products = list(Product.objects.filter(
            retailer=retailer_code, raw_brand_name=brand_name
        ).values(
            'id', 'retailer', 'raw_brand_name', 'gender', 
            'category1', 'category2', 'origin', 'price_org',
            'markup', 'calculated_price_krw', 'season'
        ))
        
        if not products:
            log_end_session(logger, 0, (datetime.now() - start_time).total_seconds(), success=True)
            return 0
        
        markup_cache = _load_markup_cache()
        price_cache = _load_price_cache()
        
        updates = []
        for product_dict in products:
            try:
                new_markup = _get_markup_bulk_dict(product_dict, markup_cache) or 1.0
                new_price = _calculate_price_bulk_dict(product_dict, new_markup, price_cache) or 0
                
                current_markup = product_dict['markup'] or 0
                current_price = float(product_dict['calculated_price_krw'] or 0)
                
                if (abs(current_markup - new_markup) > 0.001 or 
                    abs(current_price - new_price) > 0.5):
                    updates.append({
                        'id': product_dict['id'],
                        'markup': new_markup,
                        'calculated_price_krw': new_price
                    })
            except:
                continue
        
        if updates:
            product_ids = [update['id'] for update in updates]
            product_objects = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
            
            bulk_updates = []
            for update in updates:
                if update['id'] in product_objects:
                    product_obj = product_objects[update['id']]
                    product_obj.markup = update['markup']
                    product_obj.calculated_price_krw = update['calculated_price_krw']
                    bulk_updates.append(product_obj)
            
            with transaction.atomic():
                Product.objects.bulk_update(bulk_updates, ['markup', 'calculated_price_krw'])
        
        log_progress(logger, f"거래처 {retailer_code}, 브랜드 {brand_name}: {len(updates)}개 완료")
        
        # 완료 로그
        total_time = (datetime.now() - start_time).total_seconds()
        log_end_session(logger, len(updates), total_time, success=True)
        
        return len(updates)
        
    except Exception as e:
        total_time = (datetime.now() - start_time).total_seconds()
        log_error_session(logger, str(e), total_time)
        return 0