from pricing.models import BrandSetting, Retailer

def get_markup_from_product(product):
    try:
        retailer = Retailer.objects.get(code=product.retailer)
        print(f"❌ Retailer not found: {product.retailer}")
    except Retailer.DoesNotExist:
        return None

    print("🔍 마크업 계산 시도:")
    print(f" - retailer: {retailer}")
    print(f" - brand: {product.raw_brand_name}")
    print(f" - category1: {product.category1}")
    print(f" - season: {product.season}")

    # 💥 None 값 체크 (디버깅용)
    if not product.raw_brand_name:
        print("⚠️ 브랜드가 비어있음")
    if not product.category1:
        print("⚠️ category1이 비어있음")
    if not product.season:
        print("⚠️ 시즌이 비어있음")


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
