# shop/services/price_calculator.py
"""
상품 가격 계산 서비스

주요 기능:
1. 원화 판매가 계산 (공급가 기준 → 관세, VAT, 마진 등 포함)
2. 소비자가 계산 (COST × 환율 × 1.22)
3. 수동 입력 가격 우선 적용 (특정 리테일러)

전체 계산 흐름:
RawProduct → markup 적용 → price_supply → 원화가 계산 → 최종 판매가
"""

from decimal import Decimal, ROUND_CEILING
from pricing.models import (
    GlobalPricingSetting, CountryAlias, PriceFormulaRange, Retailer,
)

# =============================================================================
# 🔧 전역 상수 정의
# =============================================================================

# 수동 가격 입력을 사용하는 리테일러 목록 (원화가, 소비자가 공통)
MANUAL_PRICE_RETAILERS = ["MLKR", "KR-D-01", "KR-OFFLINE-01"]

# 소매가 계산 시 적용되는 기본 마진율 (COST × 환율 × 1.22)
DEFAULT_RETAIL_MARGIN = Decimal("1.22")

# =============================================================================
# 🛡️ 보안 함수: eval() 대신 안전한 추가비용 계산
# =============================================================================

def calculate_extra_fee_safely(formula_str, base_price):
    """
    구간별 추가 비용을 안전하게 계산 (eval() 사용 안함)
    
    지원하는 공식 형태:
    - "20000" → 고정 2만원 추가
    - "가격 * 0.05" → 상품가격의 5% 추가  
    - "가격 * 0.05 + 10000" → 상품가격의 5% + 1만원 추가
    
    Args:
        formula_str (str): DB에 저장된 공식 문자열
        base_price (Decimal): 기준 가격 (공급가 × 환율)
        
    Returns:
        Decimal: 계산된 추가 비용 (실패시 0)
    """
    try:
        formula_str = formula_str.strip()
        
        # 1. 단순 숫자 → 고정 비용
        if formula_str.isdigit():
            return Decimal(formula_str)
        
        # 2. "가격 * 계수" 형태 → 비례 비용
        if "가격 *" in formula_str and "+" not in formula_str:
            multiplier_str = formula_str.replace("가격 *", "").strip()
            multiplier = Decimal(multiplier_str)
            return base_price * multiplier
        
        # 3. "가격 * 계수 + 고정비" 형태 → 혼합 비용
        if "가격 *" in formula_str and "+" in formula_str:
            parts = formula_str.split("+")
            if len(parts) == 2:
                # 비례 부분 계산
                multiplier_str = parts[0].replace("가격 *", "").strip()
                variable_cost = base_price * Decimal(multiplier_str)
                
                # 고정 부분 계산
                fixed_cost = Decimal(parts[1].strip())
                
                return variable_cost + fixed_cost
        
        # 4. 인식할 수 없는 공식 → 0 반환
        return Decimal("0")
        
    except (ValueError, TypeError, IndexError):
        # 공식 파싱 실패시 0 반환 (안전장치)
        return Decimal("0")


# =============================================================================
# 🔄 공통 계산 로직: 중복 제거를 위한 핵심 함수
# =============================================================================

def get_global_pricing_settings():
    """
    글로벌 가격 설정값들을 조회 (환율, 배송비, VAT, 마진 등)
    
    Returns:
        dict: 가격 계산에 필요한 모든 설정값들
        {
            'exchange_rate': Decimal,     # 환율
            'shipping_fee': Decimal,      # 배송비율 (1 + %)
            'vat': Decimal,              # 부가세율 (1 + %)  
            'margin': Decimal,           # 마진율 (1 + %)
            'special_tax_rate': Decimal  # 개별소비세율 (%)
        }
    """
    try:
        global_setting = GlobalPricingSetting.objects.first()
        return {
            'exchange_rate': Decimal(str(global_setting.exchange_rate)),
            'shipping_fee': Decimal("1.0") + (Decimal(str(global_setting.shipping_fee)) / Decimal("100")),
            'vat': Decimal("1.0") + (Decimal(str(global_setting.VAT)) / Decimal("100")),
            'margin': Decimal("1.0") + (Decimal(str(global_setting.margin_rate)) / Decimal("100")),
            'special_tax_rate': Decimal(str(global_setting.special_tax_rate)) / Decimal("100")
        }
    except (AttributeError, TypeError):
        # DB 설정이 없을 경우 기본값 반환
        return {
            'exchange_rate': Decimal("1300"),    # 기본 환율
            'shipping_fee': Decimal("1.10"),     # 기본 배송비 10%
            'vat': Decimal("1.10"),             # 기본 VAT 10%
            'margin': Decimal("1.20"),          # 기본 마진 20%
            'special_tax_rate': Decimal("0.20") # 기본 개별소비세 20%
        }


def calculate_tariff_rate(category1, origin):
    """
    카테고리와 원산지를 기준으로 관세율 계산
    
    관세 적용 규칙:
    - FTA 적용 국가: 관세 면제 (1.00)
    - 의류/신발: 13% 관세 (1.13)
    - 가방/액세서리: 8% 관세 (1.08)
    - 기타: 관세 면제 (1.00)
    
    Args:
        category1 (str): 상품 카테고리 (의류, 신발, 가방, 액세서리 등)
        origin (str): 원산지 국가명
        
    Returns:
        Decimal: 관세율 (1.00 = 관세없음, 1.13 = 13% 관세)
    """
    tariff = Decimal("1.00")  # 기본값: 관세 없음
    
    try:
        # 국가별 FTA 적용 여부 확인
        country_alias = CountryAlias.objects.select_related("standard_country").get(
            origin_name=origin
        )
        
        # FTA 적용 국가면 관세 면제
        if country_alias.standard_country.fta_applicable:
            return tariff
            
    except CountryAlias.DoesNotExist:
        # 매핑되지 않은 국가는 관세 적용
        pass
    
    # FTA 미적용 국가의 관세율 적용
    if category1 in ["의류", "신발"]:
        tariff = Decimal("1.13")  # 13% 관세
    elif category1 in ["가방", "액세서리"]:
        tariff = Decimal("1.08")  # 8% 관세
    
    return tariff


def calculate_extra_fee_by_price_range(base_price):
    """
    상품 가격 구간에 따른 추가 비용 계산
    
    PriceFormulaRange 테이블에서 해당 가격 구간의 공식을 찾아
    추가 비용을 계산합니다.
    
    Args:
        base_price (Decimal): 기준 가격 (공급가 × 환율)
        
    Returns:
        Decimal: 추가 비용 (해당 구간이 없으면 0)
    """
    try:
        # 해당 가격 구간에 맞는 공식 조회
        price_range = PriceFormulaRange.objects.filter(
            min_price__lte=base_price,
            max_price__gte=base_price
        ).first()
        
        if price_range and price_range.formula:
            # 안전한 방식으로 추가 비용 계산 (eval 사용 안함)
            return calculate_extra_fee_safely(price_range.formula, base_price)
            
    except Exception:
        # 오류 발생시 추가비용 없음으로 처리
        pass
    
    return Decimal("0")


def calculate_core_price(price_supply, category1, origin, settings):
    """
    핵심 가격 계산 로직 (Product와 ProductOption 공통)
    
    계산 단계:
    1. 공급가 × 환율 = 기준가
    2. 기준가 × 배송비율 = 배송비 포함가  
    3. 관세율 적용
    4. VAT 적용
    5. 마진율 적용
    6. 개별소비세 적용 (200만원 초과시) - 추가비용 제외
    7. 구간별 추가비용 적용 (개별소비세 미적용시만)
    8. 100원 단위 올림
    
    Args:
        price_supply (Decimal): 공급가 (COST × markup)
        category1 (str): 상품 카테고리
        origin (str): 원산지
        settings (dict): 글로벌 가격 설정값들
        
    Returns:
        int: 최종 원화 판매가 (100원 단위)
    """
    # 1. 기준가 계산 (공급가 × 환율)
    base_price = price_supply * settings['exchange_rate']
    
    # 2. 관세율 계산
    tariff_rate = calculate_tariff_rate(category1, origin)
    
    # 3. 개별소비세 적용 여부 판단 (200만원 기준)
    luxury_tax_threshold = Decimal("2000000")
    
    if base_price > luxury_tax_threshold:
        # 고가 상품: 개별소비세 적용, 추가비용 제외
        taxable_base = base_price * settings['shipping_fee']
        special_tax = (base_price - luxury_tax_threshold) * settings['special_tax_rate']
        
        # (과세표준 + 개별소비세) × 관세 × VAT × 마진 (추가비용 제외)
        final_price = (taxable_base + special_tax) * tariff_rate * settings['vat'] * settings['margin']
    else:
        # 일반 상품: 개별소비세 없음, 추가비용 포함
        # 구간별 추가 비용 계산
        extra_fee = calculate_extra_fee_by_price_range(base_price)
        
        # 기준가 × 배송비 × 관세 × VAT × 마진 + 추가비용
        final_price = (base_price * settings['shipping_fee']) * tariff_rate * settings['vat'] * settings['margin'] + extra_fee
    
    # 4. 100원 단위 올림 처리
    rounded_price = (final_price / Decimal("100")).to_integral_value(rounding=ROUND_CEILING) * Decimal("100")
    
    return int(rounded_price)


# =============================================================================
# 🏷️ 메인 가격 계산 함수들
# =============================================================================

def calculate_final_price(product):
    """
    상품의 원화 판매가 계산 (calculated_price_krw)
    
    계산 우선순위:
    1. 수동 입력 원화가 (특정 리테일러만) 
    2. 자동 계산 원화가 (공급가 기준)
    
    Args:
        product: Product 또는 RawProduct 객체
        
    Returns:
        int: 계산된 원화 판매가 (None시 실패)
    """
    # Step 1: 수동 입력 가격 우선 처리
    if (hasattr(product, "manual_price_krw") and 
        product.manual_price_krw and 
        product.retailer in MANUAL_PRICE_RETAILERS):
        return int(product.manual_price_krw)
    
    # Step 2: 자동 계산을 위한 기본 데이터 검증
    if not product.price_supply or product.price_supply <= 0:
        return None
    
    # Step 3: 계산에 필요한 데이터 준비
    price_supply = Decimal(str(product.price_supply))
    category1 = getattr(product, 'category1', None) or ""
    origin = getattr(product, 'origin', None) or ""
    
    # Step 4: 글로벌 설정값 조회
    settings = get_global_pricing_settings()
    
    # Step 5: 핵심 가격 계산 로직 실행
    try:
        return calculate_core_price(price_supply, category1, origin, settings)
    except Exception:
        return None


def calculate_retail_price(product):
    """
    소비자가 계산 (retail_price_krw)
    
    계산 우선순위:
    1. 수동 입력 소비자가 (특정 리테일러만)
    2. 자동 계산 소비자가 (price_retail × 환율 × 1.22)
    
    Args:
        product: Product 또는 RawProduct 객체
        
    Returns:
        int: 계산된 소비자가 (None시 실패)
    """
    # Step 1: 수동 입력 소비자가 우선 처리
    if (hasattr(product, "manual_retail_price_krw") and 
        product.manual_retail_price_krw and 
        product.retailer in MANUAL_PRICE_RETAILERS):
        return int(product.manual_retail_price_krw)
    
    # Step 2: 자동 계산을 위한 기본 데이터 검증
    if not product.price_retail or product.price_retail <= 0:
        return None
    
    # Step 3: 환율 조회
    settings = get_global_pricing_settings()
    
    # Step 4: 소비자가 계산 (price_retail × 환율 × 1.22)
    try:
        retail_base = Decimal(str(product.price_retail))
        retail_price = retail_base * settings['exchange_rate'] * DEFAULT_RETAIL_MARGIN
        
        # 100원 단위 올림
        rounded_price = (retail_price / Decimal("100")).to_integral_value(rounding=ROUND_CEILING) * Decimal("100")
        
        return int(rounded_price)
    except Exception:
        return None


def calculate_option_final_price(option):
    """
    옵션별 원화 판매가 계산 (ProductOption용)
    
    계산 우선순위:
    1. 수동 입력 옵션 가격 (특정 리테일러만)
    2. 자동 계산 옵션 가격 (옵션 COST 기준)
    
    Args:
        option: ProductOption 객체
        
    Returns:
        int: 계산된 옵션 원화가 (None시 실패)
    """
    # Step 1: 수동 입력 옵션 가격 우선 처리
    if (hasattr(option, "manual_price_krw") and 
        option.manual_price_krw and 
        option.product.retailer in MANUAL_PRICE_RETAILERS):
            
        print(f"📝 옵션 수동 원화가 적용 → {option.manual_price_krw}")
        return int(option.manual_price_krw)
    
    # Step 2: 옵션 COST 검증
    if not option.price or option.price <= 0:
        print(f"❌ 옵션 COST 없음 또는 0: {option.price}")
        return None
    
    # Step 3: 부모 상품의 정보 활용
    product = option.product
    option_supply_price = Decimal(str(option.price))
    category1 = getattr(product, 'category1', None) or ""
    origin = getattr(product, 'origin', None) or ""
    
    # Step 4: 글로벌 설정값 조회
    settings = get_global_pricing_settings()
    
    # Step 5: 옵션 가격 계산 (상품과 동일한 로직)
    try:
        final_option_price = calculate_core_price(option_supply_price, category1, origin, settings)
        return final_option_price
        
    except Exception as e:
        return None


# =============================================================================
# 🔄 호환성 함수: 기존 코드에서 사용 중인 함수명 유지
# =============================================================================

# conversion_service.py에서 사용하는 함수들과 동일한 인터페이스 제공
# (기존 코드 수정 없이 바로 교체 가능)

# 별칭 함수들 - 기존 호출 코드 호환성 보장
def apply_price_to_product(product):
    """
    ⚠️ 현재 미사용 함수 - 삭제 예정
    
    기존 코드 호환성을 위해 남겨둠
    실제로는 models.py의 save() 메서드나 직접 계산 함수 호출 권장
    """
    # 원화가 계산
    new_price = calculate_final_price(product)
    if new_price is not None:
        product.calculated_price_krw = new_price

    # 소비자가 계산  
    new_retail_price = calculate_retail_price(product)
    if new_retail_price is not None:
        product.retail_price_krw = new_retail_price

    return product