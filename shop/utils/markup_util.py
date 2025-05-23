from pricing.models import BrandSetting, Retailer

def get_markup_from_product(product):
    try:
        retailer = Retailer.objects.get(code=product.retailer)
    except Retailer.DoesNotExist:
        return None

    # ✅ 1차: 브랜드 + 카테고리 + 시즌
    try:
        return BrandSetting.objects.get(
            retailer=retailer,
            brand_name=product.raw_brand_name,
            category1__contains=product.category1,
            season=product.season
        ).markup
    except BrandSetting.DoesNotExist:
        pass

    # ✅ 2차: 브랜드 + 카테고리 (시즌은 무시)
    try:
        return BrandSetting.objects.get(
            retailer=retailer,
            brand_name=product.raw_brand_name,
            category1__contains=product.category1
        ).markup
    except BrandSetting.DoesNotExist:
        pass

    # ✅ 3차: 브랜드 = 전체 + 카테고리 (시즌 무시)
    try:
        return BrandSetting.objects.get(
            retailer=retailer,
            brand_name='전체',
            category1__contains=product.category1
        ).markup
    except BrandSetting.DoesNotExist:
        return None
