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
        
        order_items = []
        order_date = order.created_at.strftime("%Y%m%d")
        retailer_short = retailer_obj.code.replace("IT-", "").replace("-", "")

        print(f"📦 장바구니 묶음 생성 중: {retailer_obj.name} → {len(carts)}개")

        item_counter = 1  # ✅ 항목별 고유 번호 부여
        for cart in carts:
            for cart_option in cart.options.all():
                if cart_option.product_option.product_id != cart.product.id:
                    continue

                quantity = cart_option.quantity
                if quantity > 0:
                    order_item = OrderItem.objects.create(
                        order=order,
                        product=cart.product,
                        option=cart_option.product_option,
                        quantity=quantity,
                        price_krw=cart.product.calculated_price_krw,
                    )

                    # ✅ 고유 external_order_number 생성
                    code = f"{order_date}-ORDER-{order.id}-{order_item.id}-{retailer_short}"
                    order_item.external_order_number = code
                    order_item.save()

                    # ✅ 리뷰 생성 및 재고 차감
                    create_order_review_from_order_item(order_item)
                    cart_option.product_option.stock = max(cart_option.product_option.stock - quantity, 0)
                    cart_option.product_option.save()

                    item_counter += 1

        # ✅ 주문 API 전송
        send_order_to_api(order)
        orders_created.append(order)

    # ✅ 장바구니 비우기
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