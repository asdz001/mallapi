from shop.models import RawProduct, Product, RawProductOption, ProductOption
from django.db import transaction
from django.utils.timezone import now
from django.db.models import Sum
from dictionary.models import BrandAlias, CategoryLevel1Alias, CategoryLevel2Alias, CategoryLevel3Alias
from pricing.models import FixedCountry, CountryAlias
from eventlog.services.log_service import log_conversion_failure


# 화경 목록 중 일치 해당가 있는지 검색

def match_alias(model, input_value):
    value = (input_value or "").strip().upper()
    all_aliases = model.objects.all().select_related("category")
    for alias_obj in all_aliases:
        alias_list = [alias.strip().upper() for alias in alias_obj.alias.split(",")]
        if value in alias_list:
            return alias_obj.category.name
    return None


def match_brand_alias(input_value):
    value = (input_value or "").strip().upper()
    all_aliases = BrandAlias.objects.all().select_related("brand")
    for alias_obj in all_aliases:
        alias_list = [alias.strip().upper() for alias in alias_obj.alias.split(",")]
        if value in alias_list:
            return alias_obj.brand.name
    return None


def match_country_alias(input_value):
    value = (input_value or "").strip().upper()
    all_aliases = CountryAlias.objects.all().select_related("standard_country")
    for alias_obj in all_aliases:
        alias_list = [alias.strip().upper() for alias in alias_obj.origin_name.split(",")]
        if value in alias_list:
            return alias_obj.standard_country.name
    return None


# 수동 단일 등록 필드와 함께 추가 필드 포함해 등록

def convert_or_update_product(raw_product):
    total_stock = RawProductOption.objects.filter(product=raw_product).aggregate(total=Sum("stock"))['total'] or 0
    if total_stock <= 0:
        return False

    # ✅ 여기 추가
    if not raw_product.price_org or raw_product.price_org == 0:
        reason = "원가 없음 또는 0원"
        log_conversion_failure(raw_product, reason)
        print(f"❌ [원가 누락] {raw_product.external_product_id}: {reason}")
        return False
    
    

    std_brand = match_brand_alias(raw_product.raw_brand_name)
    std_cat1 = match_alias(CategoryLevel1Alias, raw_product.gender)
    std_cat2 = match_alias(CategoryLevel2Alias, raw_product.category1)
    std_cat3 = match_alias(CategoryLevel3Alias, raw_product.category2)

    origin_input = (raw_product.origin or "").strip()
    origin_for_save = origin_input if origin_input else "-"
    std_origin = match_country_alias(origin_input) if origin_input else "-"

    brand_log = "브랜드 성공" if std_brand else f"브랜드 실패(사유: {raw_product.raw_brand_name})"
    category_log = "카테고리 성공" if std_cat1 else f"카테고리 실패(사유: {raw_product.category1})"
    origin_log = "원산지 성공" if std_origin else f"원산지 실패(사유: {raw_product.origin or '-'})"

    if not std_brand or not std_cat1 or not std_origin:
        reason = f"{brand_log} / {category_log} / {origin_log}"
        log_conversion_failure(raw_product, reason)
        print(f"❌ [실패] {raw_product.external_product_id}: {reason}")
        return False

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
            'brand_name': std_brand, 
            'product_name': raw_product.product_name,
            'sku': raw_product.sku,
            'price_retail': raw_product.price_retail,
            'price_org': raw_product.price_org,
            'discount_rate' : raw_product.discount_rate,
            'color': raw_product.color,
            'material': raw_product.material,
            'origin': std_origin or origin_for_save,
            'status': 'active',
            'created_at': raw_product.created_at,
            'updated_at': now(),
        }
    )

    raw_options = RawProductOption.objects.filter(product=raw_product)

    for opt in raw_options:
        if opt.stock <= 0:
            continue

        ProductOption.objects.update_or_create(
            product=product,
            option_name=opt.option_name,
            defaults={
                'external_option_id': opt.external_option_id,
                'stock': opt.stock,
                'price': opt.price,
            }
        )

    raw_product.status = 'converted'
    raw_product.updated_at = now()
    raw_product.save()
    return True


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
    return success_count
