# 상품 자동/수동 등록 로직 (conversion_service.py)
from shop.models import RawProduct, Product, RawProductOption, ProductOption
from django.db import transaction
from django.utils.timezone import now
from django.db.models import Sum
from dictionary.models import BrandAlias, CategoryLevel1Alias, CategoryLevel2Alias, CategoryLevel3Alias
from pricing.models import FixedCountry, CountryAlias
from eventlog.services.log_service import log_conversion_failure


# 🔍 브랜드명 원본 → 표준 브랜드명으로 치환
def resolve_standard_brand(raw_name):
    alias = BrandAlias.objects.filter(alias__iexact=raw_name).select_related('brand').first()
    return alias.brand.name if alias else None


# 🔍 카테고리: 성별 → 대분류, category1 → 중분류, category2 → 소분류
def resolve_standard_categories(gender, cat1, cat2):
    std_cat1 = CategoryLevel1Alias.objects.filter(alias__iexact=gender).first()
    std_cat2 = CategoryLevel2Alias.objects.filter(alias__iexact=cat1).first()
    std_cat3 = CategoryLevel3Alias.objects.filter(alias__iexact=cat2).first()
    return (
        std_cat1.category.name if std_cat1 else None,
        std_cat2.category.name if std_cat2 else None,
        std_cat3.category.name if std_cat3 else None,
    )


# 🔍 원산지명 → 표준국가명 치환
def resolve_standard_origin(origin_name):
    alias = CountryAlias.objects.filter(origin_name__iexact=origin_name).select_related('standard_country').first()
    return alias.standard_country.name if alias else None


# ✅ 수동 단일 등록 또는 수정용 함수 (관리자페이지에서도 호출 가능)
def convert_or_update_product(raw_product):
    # 1. 재고 확인
    total_stock = RawProductOption.objects.filter(product=raw_product).aggregate(total=Sum("stock"))['total'] or 0
    if total_stock <= 0:
        return False

    # 2. 표준화 치환
    std_brand = resolve_standard_brand(raw_product.raw_brand_name)
    std_cat1, std_cat2, std_cat3 = resolve_standard_categories(raw_product.gender, raw_product.category1, raw_product.category2)
    std_origin = resolve_standard_origin(raw_product.origin)

    # 3. 치환 실패 시 로그 남기고 중단
    if not std_brand or not std_cat1 or not std_origin:
        reason = (
            f"치환 실패 - 브랜드: {raw_product.raw_brand_name}, "
            f"카테고리: {raw_product.gender}/{raw_product.category1}/{raw_product.category2}, "
            f"원산지: {raw_product.origin}"
        )
        log_conversion_failure(raw_product, reason)

        print(f"❌ [실패] {raw_product.external_product_id}: {reason}")
        return False

    # 4. 상품 등록 또는 수정 (price_supply 제외, 필수 필드 추가 포함)
    product, created = Product.objects.update_or_create(
        external_product_id=raw_product.external_product_id,
        defaults={
            'retailer': raw_product.retailer,
            'season': raw_product.season,
            'gender': std_cat1,
            'category1': std_cat2,
            'category2': std_cat3,
            'image_url': raw_product.image_url_1,
            'raw_brand_name': raw_product.raw_brand_name,
            'product_name': raw_product.product_name,
            'sku': raw_product.sku,
            'price_retail': raw_product.price_retail,
            'price_org': raw_product.price_org,
            'color': raw_product.color,
            'material': raw_product.material,
            'origin': std_origin or raw_product.origin,
            'status': 'active',
            'created_at': raw_product.created_at,
            'updated_at': now(),
        }
    )

    # 5. 옵션 재고 동기화 (기존 옵션 삭제 후 새로 생성)
    ProductOption.objects.filter(product=product).delete()
    raw_options = RawProductOption.objects.filter(product=raw_product)
    option_objs = [
        ProductOption(
            product=product,
            external_option_id=opt.external_option_id,
            option_name=opt.option_name,
            stock=opt.stock,
        )
        for opt in raw_options if opt.stock > 0
    ]
    ProductOption.objects.bulk_create(option_objs)

    # 6. 원본 상태 업데이트
    raw_product.status = 'converted'
    raw_product.updated_at = now()
    raw_product.save()
    return True




# 자동 일괄 등록 함수 (uc804체 상품 대상)
def bulk_convert_or_update_products(batch_size=1000):
    raw_products = RawProduct.objects.filter(status__in=['pending', 'converted']).iterator()
    updated_raw_ids = []
    success_count = 0
    fail_count = 0 

    for raw_product in raw_products:
        success = convert_or_update_product(raw_product)
        if success:
            updated_raw_ids.append(raw_product.id)
            success_count += 1
        else:
            fail_count += 1

    with transaction.atomic():
        RawProduct.objects.filter(id__in=updated_raw_ids).update(status='converted', updated_at=now())

    print(f"✅ 전체 전송 완료 - 성공: {success_count}개 / 실패: {fail_count}개")      



# 리테일러별 자동 일괄 등록 함수 (uac70래창 단위 처리)
def bulk_convert_or_update_products_by_retailer(retailer_code, batch_size=1000):
    raw_products = RawProduct.objects.filter(
        retailer=retailer_code,
        status__in=['pending', 'converted']
    ).iterator()
    updated_raw_ids = []
    success_count = 0
    fail_count = 0     

    for raw_product in raw_products:
        success = convert_or_update_product(raw_product)
        if success:
            updated_raw_ids.append(raw_product.id)
            success_count += 1
        else:
            fail_count += 1

    with transaction.atomic():
        RawProduct.objects.filter(id__in=updated_raw_ids).update(status='converted', updated_at=now())


    print(f"✅ [{retailer_code}] 전송 완료 - 성공: {success_count}개 / 실패: {fail_count}개")    
