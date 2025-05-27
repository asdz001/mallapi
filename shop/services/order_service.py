from shop.models import Order, OrderItem, ProductOption
from pricing.models import Retailer
from collections import defaultdict
from django.db import transaction
from importlib import import_module



@transaction.atomic
def create_orders_from_carts(selected_carts, request):
    cart_groups = defaultdict(list)
    for cart in selected_carts:
        cart_groups[cart.product.retailer].append(cart)

    orders_created = []

    for retailer_code, carts in cart_groups.items():
        retailer_obj = Retailer.objects.get(code=retailer_code)
        order = Order.objects.create(retailer=retailer_obj)

        print(f"📦 장바구니 {cart.id} 처리 중")

        for cart in carts:
            for cart_option in cart.options.all():
                print(f" - 옵션: {cart_option.product_option.option_name}")

                if cart_option.product_option.product_id != cart.product.id:
                    continue

                quantity = cart_option.quantity  # ✅ DB에서 직접 가져오기
                if quantity > 0:
                    ...


                if quantity > 0:
                    print(f"✅ 주문 생성: {cart.product.product_name} - {cart_option.product_option.option_name} x {quantity}")
                    ...

                if quantity > 0:
                    # ✅ 1. 주문 항목 생성
                    OrderItem.objects.create(
                        order=order,
                        product=cart.product,
                        option=cart_option.product_option,
                        quantity=quantity,
                        price_krw=cart.product.calculated_price_krw,
                    )

                    # ✅ 2. 재고 차감
                    product_option = cart_option.product_option
                    product_option.stock = max(product_option.stock - quantity, 0)  # 음수 방지
                    product_option.save()

        #send_order_to_api(order)
        orders_created.append(order)

    # ✅ 3. 장바구니 삭제
    for cart in selected_carts:
        cart.options.all().delete()
        cart.delete()

    return orders_created


#api로 주문호출
def send_order_to_api(order):
    try:
        print(f"\n🛰️ [API 전송 시작] 주문번호: {order.id}, 거래처: {order.retailer.name}")

        # 하이픈 제거 → 모듈명은 _로 변환
        module_key = order.retailer.code.lower().replace("-", "_")
        module_path = f"shop.services.order.{module_key}"
        send_order = import_module(module_path).send_order

        result = send_order(order)

        if all(r.get('success') for r in result):
            order.status = "SENT"
            order.memo = "API 전송 성공"
        else:
            order.status = "FAILED"
            order.memo = "일부 항목 전송 실패"

    except Exception as e:
        print("❌ 오류 발생:", str(e))
        order.status = "FAILED"
        order.memo = f"전송 실패: {str(e)}"

    finally:
        order.save()