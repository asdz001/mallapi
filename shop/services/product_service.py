from shop.models import Product

# 상품 데이터를 저장하는 함수 (거래처 포함)
def save_products_from_api(goods, retailer_id, brand="Atelier"):
    count = 0  # 저장된 상품 수 카운트

    for item in goods:
        product_name = item.get("GoodsName") or f"ID-{item.get('ID')}"

        Product.objects.update_or_create(
            name=product_name,
            brand=brand,
            retailer=retailer_id,  # 거래처 정보 저장
            defaults={
                "price": 0,  # 가격은 일단 0, 나중에 PriceList로 업데이트
                "stock": int(item.get("InStock", 0)),
                "status": "active"
            }
        )
        count += 1

    return count

