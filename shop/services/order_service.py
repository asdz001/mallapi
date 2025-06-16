from shop.models import Order, OrderItem, ProductOption
from pricing.models import Retailer
from collections import defaultdict
from django.db import transaction
from importlib import import_module
from orderreview.models import OrderReview



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
                    order_item = OrderItem.objects.create(
                        order=order,
                        product=cart.product,
                        option=cart_option.product_option,
                        quantity=quantity,
                        price_krw=cart.product.calculated_price_krw,
                    )

                    # ✅ 2. 주문리뷰 자동 생성
                    create_order_review_from_order_item(order_item)

                    # ✅ 2. 재고 차감
                    product_option = cart_option.product_option
                    product_option.stock = max(product_option.stock - quantity, 0)  # 음수 방지
                    product_option.save()

        send_order_to_api(order)
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

        # 거래처별 모듈 import
        ATELIER_CODES = {"MINETTI", "CUCCUINI", "BINI", "IT-C-02", "IT-M-01", "IT-B-02", "TEST-HUB"}
        module_key = "atelier" if order.retailer.code.upper() in ATELIER_CODES else order.retailer.code.lower().replace("-", "_")
        module_path = f"shop.services.order.{module_key}"
        send_order = import_module(module_path).send_order

        # ✅ 거래처 API에 주문 전송 → 결과는 무조건 표준 형태여야 함
        result = send_order(order)

        has_failed = False

        for res in result:
            barcode = res.get("sku")
            item_id = res.get("item_id")
            success = res.get("success", False)
            reason = res.get("reason", "")


            item = order.items.filter(id=item_id, option__external_option_id=barcode).first()
            if not item:
                continue

            item.order_status = "SENT" if success else "FAILED"
            item.order_message = "" if success else reason
            item.save()

            if not success:
                has_failed = True

        if has_failed:
            order.status = "FAILED"
            order.memo = "일부 상품 전송 실패"
        else:
            order.status = "SENT"
            order.memo = "API 전송 성공"

    except Exception as e:
        print("❌ 오류 발생:", str(e))
        order.status = "FAILED"
        order.memo = f"전송 실패: {str(e)}"

        # 예외 발생 시 전체 상품 실패 처리
        for item in order.items.all():
            item.order_status = "FAILED"
            item.order_message = str(e)
            item.save()

    finally:
        order.save()

def create_order_review_from_order_item(order_item):
    """
    SHOP에서 주문이 생성될 때 호출되어, 주문 항목당 OrderReview를 자동 생성
    """
    if not OrderReview.objects.filter(order_item=order_item).exists():
        OrderReview.objects.create(
            order_item=order_item,
            retailer=order_item.order.retailer,  # 주문에 있는 거래처 정보
            status="PENDING",  # 초기 상태는 미확인
        )        