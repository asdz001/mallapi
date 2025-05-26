from decimal import Decimal , ROUND_CEILING
from pricing.models import ( GlobalPricingSetting, CountryAlias, PriceFormulaRange, Retailer,)
from shop.utils.markup_util import get_markup_from_product


def calculate_final_price(product):
    price_supply = product.price_supply
    category1 = product.category1
    retailer_code = product.retailer
    origin = product.origin

    
    #print("\n[🧮 가격 계산 디버깅]")
    #print(f" - 입력된 retailer 문자열: {retailer_code}")



    try:
        retailer_obj = Retailer.objects.get(code=retailer_code)
        #print(f" - Retailer 객체 변환 성공: {retailer_obj}")
    except Retailer.DoesNotExist:
        retailer_obj = None
        print(f"❌ [오류] Retailer 변환 실패: {retailer_code}")
        return None  # 혹은 fallback 값 처리



    # Step 2: 글로벌 설정
    try:
        global_setting = GlobalPricingSetting.objects.first()
        exchange_rate = Decimal(str(global_setting.exchange_rate))
        shipping_fee = Decimal("1.0") + (Decimal(str(global_setting.shipping_fee)) / Decimal("100"))
        vat = Decimal("1.0") + (Decimal(str(global_setting.VAT)) / Decimal("100"))
        margin = Decimal("1.0") + (Decimal(str(global_setting.margin_rate)) / Decimal("100"))
        special_tax_rate = Decimal(str(global_setting.special_tax_rate)) / Decimal("100")
    except:
        exchange_rate = Decimal("1300")
        shipping_fee = Decimal("1.10")
        vat = Decimal("1.10")
        margin = Decimal("1.20")
        special_tax_rate = Decimal("0.20")

    # Step 3: 관세
    tariff = Decimal("1.00")
    try:
        alias = CountryAlias.objects.select_related("standard_country").get(origin_name=origin)
        fta = alias.standard_country.fta_applicable
        #print(f" - 원산지 매핑 성공: {origin} → {alias.standard_country.name}, FTA 적용: {fta}")

        if not fta:
            if category1 in ["의류", "신발"]:
                tariff = Decimal("1.13")
            elif category1 in ["가방", "액세서리"]:
                tariff = Decimal("1.08")
            #else:
                #print(f" - 관세 적용 예외 카테고리: {category1} → 기본값 유지")
        #else:
                #print(" - FTA 적용 국가이므로 관세 없음 (1.00)")
    except CountryAlias.DoesNotExist:
        #print(f"❌ [FTA 매핑 실패] 원산지 '{origin}'에 대한 치환 국가명 없음 → 관세 부과 대상")
        if category1 in ["의류", "신발"]:
            tariff = Decimal("1.13")
        elif category1 in ["가방", "액세서리"]:
            tariff = Decimal("1.08")


    base = price_supply * exchange_rate
    # Step 4: 구간별 추가금액 (텍스트 수식 평가)
    try:
        extra_range = PriceFormulaRange.objects.filter(
            min_price__lte=base,
            max_price__gte=base
        ).first()
        if extra_range:
            formula = extra_range.formula.replace("가격", str(base))
            extra_fee = Decimal(str(eval(formula)))
        else:
            extra_fee = Decimal("0")
    except:
        extra_fee = Decimal("0")

    # 디버깅 로그 출력
    #print("\n[🧮 가격 계산 디버깅]")
    #print(f" - 공급가: {price_supply}")
    #print(f" - 환율: {exchange_rate}")
    #print(f" - 배송비: {shipping_fee}")
    #print(f" - 관세: {tariff}")
    #print(f" - VAT: {vat}")
    #print(f" - 마진율: {margin}")
    #print(f" - 개소세율: {special_tax_rate}")
    #print(f" - base: {base}")
    #print(f" - extra_fee: {extra_fee}")

    if base > Decimal("2000000"):
        taxable_base = base * shipping_fee
        special_tax = (base - Decimal("2000000")) * special_tax_rate
        result = (taxable_base + special_tax) * tariff * vat * margin + extra_fee
        #print(" - 개소세 적용: YES")
    else:
        result = (base * shipping_fee) * tariff * vat * margin + extra_fee
        #print(" - 개소세 적용: NO")

    rounded_result = (result / Decimal("1000")).to_integral_value(rounding=ROUND_CEILING) * Decimal("1000")
    #print(f" - 1000원 단위로 반올림된 최종 금액: {rounded_result}\n")

    return int(rounded_result)

def apply_price_to_product(product):
    product.calculated_price_krw = calculate_final_price(product)
    return product
