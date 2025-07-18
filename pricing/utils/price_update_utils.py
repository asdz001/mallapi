# pricing/utils/optimized_price_update_utils.py - 진짜 버전 1 방식 복구

from shop.models import Product
from pricing.models import BrandSetting, GlobalPricingSetting, FixedCountry, Retailer, CountryAlias, PriceFormulaRange
from django.db import transaction
from decimal import Decimal, ROUND_CEILING

def update_all_products_pricing():
    """🚀 진짜 버전 1 방식: values() + 딕셔너리 계산 + 빠른 속도"""
    print("🚀 최적화된 전체 상품 가격 업데이트 시작...")
    
    # 1단계: 필요한 필드만 딕셔너리로 가져오기 (버전 1 방식)
    print("📊 필요한 데이터 일괄 로딩...")
    products = list(Product.objects.values(
        'id', 'retailer', 'raw_brand_name', 'gender', 
        'category1', 'category2', 'origin', 'price_org',
        'markup', 'calculated_price_krw', 'season'
    ))
    
    # 캐시 데이터 로드 (한번만)
    markup_cache = _load_markup_cache_exact()
    price_cache = _load_price_cache_exact()
    
    print(f"📊 로딩 완료 - 상품: {len(products):,}개")
    
    # 2단계: 딕셔너리 기반 빠른 계산 (버전 1 방식)
    print("🧮 벌크 계산 시작...")
    updates = []
    
    for product_dict in products:
        # 딕셔너리 데이터로 계산 (빠름!)
        new_markup = _get_markup_bulk_dict(product_dict, markup_cache) or 1.0
        new_price = _calculate_price_bulk_dict(product_dict, new_markup, price_cache) or 0
        
        # 변경 감지
        current_markup = product_dict['markup'] or 0
        current_price = float(product_dict['calculated_price_krw'] or 0)
        
        markup_changed = abs(current_markup - new_markup) > 0.001
        price_changed = abs(current_price - new_price) > 0.5
        
        if markup_changed or price_changed:
            updates.append({
                'id': product_dict['id'],
                'markup': new_markup,
                'calculated_price_krw': new_price
            })
    
    print(f"🔄 계산 완료 - {len(updates):,}개 상품 변경 감지")
    
    # 3단계: 한번에 저장 (버전 1 방식)
    if updates:
        print("💾 벌크 저장 시작...")
        
        # Product 객체들을 id로 한번에 조회
        product_ids = [update['id'] for update in updates]
        product_objects = {
            p.id: p for p in Product.objects.filter(id__in=product_ids)
        }
        
        # 업데이트할 객체들 준비
        bulk_updates = []
        for update in updates:
            product_obj = product_objects[update['id']]
            product_obj.markup = update['markup']
            product_obj.calculated_price_krw = update['calculated_price_krw']
            bulk_updates.append(product_obj)
        
        # 한번에 업데이트
        with transaction.atomic():
            Product.objects.bulk_update(
                bulk_updates, 
                ['markup', 'calculated_price_krw'],
                batch_size=1000
            )
        
        print(f"✅ 벌크 저장 완료 - {len(updates):,}개 상품 업데이트")
    else:
        print("📋 업데이트할 상품이 없습니다")
    
    return len(updates)


def _load_markup_cache_exact():
    """마크업 캐시 로드 (기존 함수 로직 반영)"""
    cache = {
        'retailers': {},
        'brand_settings': {}
    }
    
    # Retailer 캐시
    for retailer in Retailer.objects.all():
        cache['retailers'][retailer.code] = retailer
    
    # BrandSetting + BrandMarkupDetail 캐시
    brand_settings = BrandSetting.objects.filter(is_active=True).order_by('priority', 'id')
    
    for setting in brand_settings:
        retailer_code = setting.retailer.code
        if retailer_code not in cache['brand_settings']:
            cache['brand_settings'][retailer_code] = []
        
        cache['brand_settings'][retailer_code].append({
            'id': setting.id,
            'brand_name': setting.brand_name,
            'seasons': setting.seasons,
            'priority': setting.priority,
            'markups': []
        })
    
    # BrandMarkupDetail 캐시
    for setting in brand_settings:
        retailer_code = setting.retailer.code
        setting_data = None
        
        for bs in cache['brand_settings'][retailer_code]:
            if bs['id'] == setting.id:
                setting_data = bs
                break
        
        if setting_data:
            for markup in setting.markups.filter(is_active=True):
                setting_data['markups'].append({
                    'gender': markup.gender,
                    'category': markup.category,
                    'markup': markup.markup,
                    'is_active': markup.is_active
                })
    
    return cache


def _load_price_cache_exact():
    """가격 계산 캐시 로드 (기존 함수 로직 반영)"""
    cache = {
        'retailers': {},
        'global_setting': None,
        'country_aliases': {},
        'price_formula_ranges': []
    }
    
    # Retailer 캐시
    for retailer in Retailer.objects.all():
        cache['retailers'][retailer.code] = retailer
    
    # GlobalPricingSetting 캐시
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
            'exchange_rate': Decimal("1600"),
            'shipping_fee': Decimal("1.50"),
            'vat': Decimal("1.10"),
            'margin': Decimal("1.20"),
            'special_tax_rate': Decimal("0.20")
        }
    
    # CountryAlias 캐시
    for alias in CountryAlias.objects.select_related("standard_country").all():
        cache['country_aliases'][alias.origin_name] = {
            'standard_country_name': alias.standard_country.name,
            'fta_applicable': alias.standard_country.fta_applicable
        }
    
    # PriceFormulaRange 캐시
    for range_obj in PriceFormulaRange.objects.all():
        cache['price_formula_ranges'].append({
            'min_price': range_obj.min_price,
            'max_price': range_obj.max_price,
            'formula': range_obj.formula
        })
    
    return cache


def _get_markup_bulk_dict(product_dict, markup_cache):
    """딕셔너리 기반 마크업 계산 (버전 1 방식 + 기존 함수 로직)"""
    retailer_code = product_dict['retailer']
    product_brand = product_dict['raw_brand_name']
    product_gender = product_dict['gender'] or '전체'
    product_category = product_dict['category1'] or '전체'
    product_season = product_dict['season'] or '전체'
    
    # 거래처 확인
    if retailer_code not in markup_cache['retailers']:
        return None
    
    # 필수값 검증
    if not product_brand:
        return None
    
    # 성별 또는 카테고리가 빈칸이면 특별 처리
    if not product_dict['gender'] or not product_dict['category1']:
        markup = _get_fallback_markup_dict(retailer_code, markup_cache)
        if markup is not None:
            return markup
    
    # 브랜드 설정 조회
    if retailer_code not in markup_cache['brand_settings']:
        return None
    
    brand_settings = markup_cache['brand_settings'][retailer_code]
    
    if not brand_settings:
        return None
    
    # 우선순위 순으로 검사
    for setting in brand_settings:
        # 브랜드 매칭
        if not _is_brand_match_dict(setting['brand_name'], product_brand):
            continue
        
        # 시즌 매칭
        if not _is_season_match_dict(setting, product_season):
            continue
        
        # 성별 + 카테고리 매칭
        markup = _find_markup_detail_dict(setting, product_gender, product_category)
        if markup is not None:
            return markup
    
    return None


def _get_fallback_markup_dict(retailer_code, markup_cache):
    """딕셔너리 기반 fallback 마크업"""
    if retailer_code not in markup_cache['brand_settings']:
        return None
    
    brand_settings = markup_cache['brand_settings'][retailer_code]
    sorted_settings = sorted(brand_settings, key=lambda x: (-x['priority'], -x['id']))
    
    for setting in sorted_settings:
        markup = _find_markup_detail_dict(setting, "전체", "전체")
        if markup is not None:
            return markup
    
    return None


def _is_brand_match_dict(setting_brand, product_brand):
    """딕셔너리 기반 브랜드 매칭"""
    if setting_brand == "전체":
        return True
    
    if not product_brand or product_brand.strip() == "":
        return False
    
    return setting_brand == product_brand


def _is_season_match_dict(brand_setting, product_season):
    """딕셔너리 기반 시즌 매칭"""
    if not brand_setting['seasons']:
        return True
    
    setting_seasons_raw = brand_setting['seasons'].strip()
    
    if "전체" in setting_seasons_raw:
        return True
    
    if not product_season or product_season.strip() == "":
        return False
    
    setting_seasons = [s.strip() for s in setting_seasons_raw.split(',') if s.strip()]
    return product_season in setting_seasons


def _find_markup_detail_dict(brand_setting, product_gender, product_category):
    """딕셔너리 기반 마크업 상세 검색"""
    if not product_gender or product_gender.strip() == "":
        product_gender = "전체"
    if not product_category or product_category.strip() == "":
        product_category = "전체"
    
    search_scenarios = [
        (product_gender, product_category),
        (product_gender, "전체"),
        ("전체", product_category),
        ("전체", "전체"),
    ]
    
    for gender, category in search_scenarios:
        for markup_detail in brand_setting['markups']:
            if (markup_detail['gender'] == gender and 
                markup_detail['category'] == category and 
                markup_detail['is_active']):
                return markup_detail['markup']
    
    return None


def _calculate_price_bulk_dict(product_dict, markup, price_cache):
    """딕셔너리 기반 가격 계산 (버전 1 방식 + 기존 함수 로직)"""
    # price_supply 계산 (기존 로직: price_org * markup)
    price_org = product_dict['price_org'] or 0
    if price_org <= 0:
        return 0
    
    price_supply = Decimal(str(price_org)) * Decimal(str(markup))
    
    category1 = product_dict['category1']
    retailer_code = product_dict['retailer']
    origin = product_dict['origin']
    
    # Retailer 확인
    if retailer_code not in price_cache['retailers']:
        print(f"❌ [오류] Retailer 변환 실패: {retailer_code}")
        return None
    
    # 글로벌 설정
    global_setting = price_cache['global_setting']
    exchange_rate = global_setting['exchange_rate']
    shipping_fee = global_setting['shipping_fee']
    vat = global_setting['vat']
    margin = global_setting['margin']
    special_tax_rate = global_setting['special_tax_rate']
    
    # 관세 계산
    tariff = Decimal("1.00")
    
    if origin in price_cache['country_aliases']:
        alias_data = price_cache['country_aliases'][origin]
        fta = alias_data['fta_applicable']
        
        if not fta:
            if category1 in ["의류", "신발"]:
                tariff = Decimal("1.13")
            elif category1 in ["가방", "액세서리"]:
                tariff = Decimal("1.08")
    else:
        # CountryAlias.DoesNotExist 케이스
        if category1 in ["의류", "신발"]:
            tariff = Decimal("1.13")
        elif category1 in ["가방", "액세서리"]:
            tariff = Decimal("1.08")
    
    base = price_supply * exchange_rate
    
    # 구간별 추가금액
    extra_fee = Decimal("0")
    try:
        for range_data in price_cache['price_formula_ranges']:
            if (range_data['min_price'] <= base <= range_data['max_price']):
                formula = range_data['formula'].replace("가격", str(base))
                extra_fee = Decimal(str(eval(formula)))
                break
    except:
        extra_fee = Decimal("0")
    
    # 최종 계산
    if base > Decimal("2000000"):
        taxable_base = base * shipping_fee
        special_tax = (base - Decimal("2000000")) * special_tax_rate
        result = (taxable_base + special_tax) * tariff * vat * margin + extra_fee
    else:
        result = (base * shipping_fee) * tariff * vat * margin + extra_fee
    
    # 1000원 단위 반올림
    rounded_result = (result / Decimal("1000")).to_integral_value(rounding=ROUND_CEILING) * Decimal("1000")
    
    return int(rounded_result)


def update_products_by_retailer(retailer_code):
    """거래처별 업데이트 (버전 1 방식)"""
    print(f"🚀 거래처 {retailer_code} 상품 업데이트 시작...")
    
    products = list(Product.objects.filter(retailer=retailer_code).values(
        'id', 'retailer', 'raw_brand_name', 'gender', 
        'category1', 'category2', 'origin', 'price_org',
        'markup', 'calculated_price_krw', 'season'
    ))
    
    if not products:
        print(f"📋 거래처 {retailer_code}에 상품이 없습니다")
        return 0
    
    markup_cache = _load_markup_cache_exact()
    price_cache = _load_price_cache_exact()
    
    updates = []
    for product_dict in products:
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
    
    if updates:
        product_ids = [update['id'] for update in updates]
        product_objects = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
        
        bulk_updates = []
        for update in updates:
            product_obj = product_objects[update['id']]
            product_obj.markup = update['markup']
            product_obj.calculated_price_krw = update['calculated_price_krw']
            bulk_updates.append(product_obj)
        
        with transaction.atomic():
            Product.objects.bulk_update(bulk_updates, ['markup', 'calculated_price_krw'])
        
        print(f"✅ 거래처 {retailer_code}: {len(updates)}개 상품 업데이트 완료")
    
    return len(updates)


def update_products_by_brand_and_retailer(retailer_code, brand_name):
    """거래처+브랜드별 업데이트 (버전 1 방식)"""
    if brand_name in ['전체', 'ETC']:
        return update_products_by_retailer(retailer_code)
    
    products = list(Product.objects.filter(
        retailer=retailer_code,
        raw_brand_name=brand_name
    ).values(
        'id', 'retailer', 'raw_brand_name', 'gender', 
        'category1', 'category2', 'origin', 'price_org',
        'markup', 'calculated_price_krw', 'season'
    ))
    
    if not products:
        return 0
    
    markup_cache = _load_markup_cache_exact()
    price_cache = _load_price_cache_exact()
    
    updates = []
    for product_dict in products:
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
    
    if updates:
        product_ids = [update['id'] for update in updates]
        product_objects = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
        
        bulk_updates = []
        for update in updates:
            product_obj = product_objects[update['id']]
            product_obj.markup = update['markup']
            product_obj.calculated_price_krw = update['calculated_price_krw']
            bulk_updates.append(product_obj)
        
        with transaction.atomic():
            Product.objects.bulk_update(updates, ['markup', 'calculated_price_krw'])
    
    return len(updates)