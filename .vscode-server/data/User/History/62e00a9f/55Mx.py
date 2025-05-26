from pricing.models import BrandSetting, Retailer

def get_markup_from_product(product):
    try:
        retailer = Retailer.objects.get(code=product.retailer)
    except Retailer.DoesNotExist:
        #print(f"❌ Retailer not found: {product.retailer}")
        return None
    
    # 💥 category1이 None이면 쿼리하지 않도록 방어 처리
    if not product.raw_brand_name or not product.category1:
        print("⚠️ [마크업 계산 스킵] 필수값 누락")
        print(f" - 상품 ID: {product.id}")
        print(f" - 브랜드: {product.raw_brand_name}")
        print(f" - 카테고리1: {product.category1}")
        print(f" - 시즌: {product.season}")
        return None
        

    try:
        return BrandSetting.objects.get(
            retailer=retailer,
            brand_name=product.raw_brand_name,
            category1__contains=product.category1,
            season=product.season
        ).markup
    except BrandSetting.DoesNotExist:
        pass
    except Exception as e:
        print("❗ 예외 발생 (1차):", e)
        print("⚠️ 브랜드:", product.raw_brand_name)
        print("⚠️ 카테고리:", product.category1)
        print("⚠️ 시즌:", product.season)
        
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

    #except Exception as e:
        #print(f"💥 예외 발생 (1차 쿼리): {e}")

    # ✅ 2차: 브랜드 + 카테고리 (시즌은 무시)
    try:
        return BrandSetting.objects.get(
            retailer=retailer,
            brand_name=product.raw_brand_name,
            category1__contains=product.category1
        ).markup
    except BrandSetting.DoesNotExist:
        pass

    #except Exception as e:
        #print(f"💥 예외 발생 (1차 쿼리): {e}")

    # ✅ 3차: 브랜드 = 전체 + 카테고리 (시즌 무시)
    try:
        return BrandSetting.objects.get(
            retailer=retailer,
            brand_name='전체',
            category1__contains=product.category1
        ).markup
    except BrandSetting.DoesNotExist:
        return None
    
    #except Exception as e:
        #print(f"💥 예외 발생 (1차 쿼리): {e}")
