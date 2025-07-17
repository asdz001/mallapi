# pricing/utils/price_update_utils.py - 기존 함수 활용하는 벌크 처리

from shop.models import Product
from shop.utils.markup_util import get_markup_from_product
from shop.services.price_calculator import calculate_final_price
from django.db import transaction


def update_all_products_pricing():
    """모든 상품의 마크업과 원화가를 벌크 방식으로 재계산 - 기존 함수 활용"""
    try:
        print("📊 상품 데이터 수집 중...")
        
        # 모든 상품을 한 번에 가져오기
        all_products = Product.objects.all()
        total_count = all_products.count()
        
        print(f"📊 총 {total_count}개 상품 처리 시작...")
        
        # 청크 단위로 처리하되 벌크 업데이트 적용
        chunk_size = 1000
        updated_count = 0
        processed = 0
        
        for offset in range(0, total_count, chunk_size):
            print(f"📦 청크 처리 중: {offset//chunk_size + 1}/{(total_count-1)//chunk_size + 1}")
            
            # 청크별로 상품 가져오기
            chunk_products = list(all_products[offset:offset + chunk_size])
            chunk_updates = []
            
            # 각 상품에 대해 기존 함수로 계산
            for product in chunk_products:
                old_markup = product.markup
                old_price = product.calculated_price_krw
                
                # 기존 함수 활용 (검증된 로직)
                new_markup = get_markup_from_product(product)
                new_price = calculate_final_price(product)
                
                # 변경사항이 있는 경우만 업데이트 대상에 추가
                if old_markup != new_markup or old_price != new_price:
                    product.markup = new_markup
                    product.calculated_price_krw = new_price
                    chunk_updates.append(product)
            
            # 청크별로 벌크 업데이트
            if chunk_updates:
                with transaction.atomic():
                    Product.objects.bulk_update(
                        chunk_updates, 
                        ['markup', 'calculated_price_krw'], 
                        batch_size=500
                    )
                    updated_count += len(chunk_updates)
                    print(f"💾 {len(chunk_updates)}개 상품 업데이트 완료")
            
            processed += len(chunk_products)
        
        print(f"✅ 전체 업데이트 완료: {updated_count}개 상품")
        return updated_count
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        raise e


def update_products_by_retailer(retailer_code):
    """특정 거래처의 상품들만 벌크 방식으로 재계산 - 기존 함수 활용"""
    print(f"📊 거래처 {retailer_code} 상품 업데이트 시작...")
    
    try:
        # 해당 거래처 상품만 필터링
        retailer_products = Product.objects.filter(retailer=retailer_code)
        total_count = retailer_products.count()
        
        if total_count == 0:
            print(f"📋 거래처 {retailer_code}에 상품이 없습니다.")
            return 0
        
        print(f"📊 거래처 {retailer_code}: {total_count}개 상품 처리 시작...")
        
        # 청크 단위로 처리
        chunk_size = 1000
        updated_count = 0
        
        for offset in range(0, total_count, chunk_size):
            chunk_products = list(retailer_products[offset:offset + chunk_size])
            chunk_updates = []
            
            for product in chunk_products:
                old_markup = product.markup
                old_price = product.calculated_price_krw
                
                # 기존 함수 활용
                new_markup = get_markup_from_product(product)
                new_price = calculate_final_price(product)
                
                if old_markup != new_markup or old_price != new_price:
                    product.markup = new_markup
                    product.calculated_price_krw = new_price
                    chunk_updates.append(product)
            
            # 벌크 업데이트
            if chunk_updates:
                with transaction.atomic():
                    Product.objects.bulk_update(
                        chunk_updates, 
                        ['markup', 'calculated_price_krw'], 
                        batch_size=500
                    )
                    updated_count += len(chunk_updates)
        
        print(f"✅ 거래처 {retailer_code} 업데이트 완료: {updated_count}개 상품")
        return updated_count
        
    except Exception as e:
        print(f"❌ 거래처 {retailer_code} 업데이트 실패: {str(e)}")
        raise e


def update_products_by_brand_and_retailer(retailer_code, brand_name):
    """특정 거래처+브랜드의 상품들만 벌크 방식으로 업데이트 - 기존 함수 활용"""
    print(f"📊 거래처 {retailer_code}, 브랜드 {brand_name} 상품 업데이트 시작...")
    
    try:
        # 특정 거래처+브랜드 상품만 필터링
        if brand_name in ['전체', 'ETC']:
            # 전체 브랜드인 경우 거래처 전체 처리
            return update_products_by_retailer(retailer_code)
        else:
            # 특정 브랜드만 필터링
            brand_products = Product.objects.filter(
                retailer=retailer_code,
                raw_brand_name=brand_name
            )
            total_count = brand_products.count()
            
            if total_count == 0:
                print(f"📋 거래처 {retailer_code}, 브랜드 {brand_name}에 상품이 없습니다.")
                return 0
            
            print(f"📊 거래처 {retailer_code}, 브랜드 {brand_name}: {total_count}개 상품 처리...")
            
            updated_count = 0
            chunk_size = 500  # 브랜드별은 상품 수가 적으므로 작은 청크
            
            for offset in range(0, total_count, chunk_size):
                chunk_products = list(brand_products[offset:offset + chunk_size])
                chunk_updates = []
                
                for product in chunk_products:
                    old_markup = product.markup
                    old_price = product.calculated_price_krw
                    
                    # 기존 함수 활용
                    new_markup = get_markup_from_product(product)
                    new_price = calculate_final_price(product)
                    
                    if old_markup != new_markup or old_price != new_price:
                        product.markup = new_markup
                        product.calculated_price_krw = new_price
                        chunk_updates.append(product)
                
                # 벌크 업데이트
                if chunk_updates:
                    with transaction.atomic():
                        Product.objects.bulk_update(
                            chunk_updates, 
                            ['markup', 'calculated_price_krw'], 
                            batch_size=500
                        )
                        updated_count += len(chunk_updates)
            
            print(f"✅ 거래처 {retailer_code}, 브랜드 {brand_name} 업데이트 완료: {updated_count}개 상품")
            return updated_count
        
    except Exception as e:
        print(f"❌ 거래처 {retailer_code}, 브랜드 {brand_name} 업데이트 실패: {str(e)}")
        raise e