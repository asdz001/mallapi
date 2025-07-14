from shop.models import Order, OrderItem, ProductOption
from pricing.models import Retailer
from collections import defaultdict
from django.db import transaction
from importlib import import_module
from orderreview.models import OrderReview
import json  # JSON 형식 로그 기록용
from utils.order_logger import logger, log_order_send
from shop.services.price_calculator import calculate_final_price
from shop.utils.markup_util import get_markup_from_product

@transaction.atomic
def create_orders_from_carts(selected_carts, request):
    cart_groups = defaultdict(list)
    for cart in selected_carts:
        cart_groups[cart.product.retailer].append(cart)

    orders_created = []

    for retailer_code, carts in cart_groups.items():
        retailer_obj = Retailer.objects.get(code=retailer_code)
        order = Order.objects.create(
            retailer=retailer_obj,
            created_by=request.user,
        )

        order_items = []  # ✅ 원래 코드 유지 (혹시 모를 참조용)
        order_date = order.created_at.strftime("%Y%m%d")
        retailer_short = retailer_obj.code.replace("IT-", "").replace("-", "")

        print(f"📦 장바구니 묶음 생성 중: {retailer_obj.name} → {len(carts)}개")
        item_counter = 1  # ✅ 항목별 고유 번호 부여

        for cart in carts:
            print(f"📦 장바구니 {cart.id} 처리 중")
            
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
                        option_price=cart_option.product_option.price,  # ✅ 옵션 단가
                        price_org=cart.product.price_org,   # ✅ 원가
                        price_supply=cart.product.price_supply,  # ✅ 공급가
                        markup=get_markup_from_product(cart.product),  # ✅ 마크업율
                        price_krw=calculate_final_price(cart.product),
                    )

                    # ✅ 고유 external_order_number 생성
                    code = f"{order_date}-ORDER-{order.id}-{order_item.id}-{retailer_short}"
                    order_item.external_order_number = code
                    order_item.save()

                    # ✅ 재고 차감 (리뷰는 API 전송 성공 후에만 생성)
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


def send_order_to_api(order):
    """API로 주문 전송"""
    try:
        print(f"\n🛰️ [API 전송 시작] 주문번호: {order.id}, 거래처: {order.retailer.name}")
        logger.info(f"[START] 주문번호: {order.id}, 거래처: {order.retailer.code} → 주문 전송 준비됨")

        ATELIER_CODES = {"MINETTI", "CUCCUINI", "BINI", "IT-C-02", "IT-M-01", "IT-B-02", "TEST-HUB"}
        module_key = "atelier" if order.retailer.code.upper() in ATELIER_CODES else order.retailer.code.lower().replace("-", "_")
        module_path = f"shop.services.order.{module_key}"
        send_order = import_module(module_path).send_order

        result, payload_data, response_data = send_order(order)
        logger.info(f"[RESULT] 주문번호: {order.id} 응답: {json.dumps(result, ensure_ascii=False)}")

        has_failed = False
        has_soldout = False

        for res in result:
            barcode = res.get("sku")
            item_id = res.get("item_id")
            success = res.get("success", False)
            reason = res.get("reason", "")
            stock = res.get("stock", -1)

            item = order.items.filter(id=item_id, option__external_option_id=barcode).first()
            if not item:
                continue

            # ✅ 상태 설정 및 리뷰 생성
            if success:
                item.order_status = "SENT"
                item.order_message = ""
                # ✅ 성공한 경우에만 리뷰 생성
                create_order_review_from_order_item(item)
                print(f"✅ 성공 처리: {barcode} → SENT")
            else:
                if stock == 0:
                    item.order_status = "SOLDOUT"
                    item.order_message = f"품절 ({reason})"
                    has_soldout = True
                    print(f"🚫 품절 처리: {barcode} → SOLDOUT (재고: {stock})")
                else:
                    item.order_status = "FAILED"
                    item.order_message = reason
                    has_failed = True
                    print(f"❌ 실패 처리: {barcode} → FAILED: {reason}")

            item.save()

        # ✅ 주문 전체 상태 설정
        if has_failed and has_soldout:
            order.status = "PARTIAL"
            order.memo = "일부 품절, 일부 실패"
        elif has_soldout:
            order.status = "SOLDOUT"
            order.memo = "품절"
        elif has_failed:
            order.status = "FAILED"
            order.memo = "전송 실패"
        else:
            order.status = "SENT"
            order.memo = "API 전송 성공"

        # ✅ 로그 기록
        log_order_send(
            order_id=order.id,
            retailer_name=order.retailer.name,
            items=[{
                "sku": res.get("sku"),
                "quantity": order.items.get(id=res.get("item_id")).quantity
            } for res in result],
            success=not (has_failed or has_soldout),
            payload=payload_data,
            response=response_data,
            reason="품절" if has_soldout and not has_failed else ("실패" if has_failed else "")
        )

    except Exception as e:
        print("❌ 오류 발생:", str(e))
        logger.error(f"[ERROR] 주문번호: {order.id} 전송 실패 → {str(e)}", exc_info=True)
        order.status = "FAILED"
        order.memo = f"전송 실패: {str(e)}"

        for item in order.items.all():
            item.order_status = "FAILED"
            item.order_message = str(e)
            item.save()

        log_order_send(
            order_id=order.id,
            retailer_name=order.retailer.name,
            items=[{
                "sku": item.option.external_option_id,
                "quantity": item.quantity
            } for item in order.items.all()],
            success=False,
            reason=str(e)
        )

    finally:
        # ✅ 최종 상태 확인 및 저장
        item_statuses = list(order.items.values_list("order_status", flat=True))
        print(f"📊 최종 아이템 상태들: {item_statuses}")
        print(f"📊 최종 주문 상태: {order.status}")
        order.save()


def create_order_review_from_order_item(order_item):
    """주문 아이템으로부터 오더 리뷰 생성 (SENT 상태일 때만)"""
    status = (order_item.order_status or "").strip().upper()
    if status != "SENT":
        print(f"⏭️ 전송 실패 항목은 오더뷰 생성 제외: {order_item.id} (상태: {status})")
        return

    # ✅ 중복 생성 방지
    if OrderReview.objects.filter(order_item=order_item).exists():
        print(f"⏭️ 이미 리뷰가 존재함: {order_item.id}")
        return

    OrderReview.objects.create(
        order_item=order_item,
        retailer=order_item.order.retailer,
        status="PENDING",
    )
    print(f"✅ 리뷰 생성 완료: OrderItem {order_item.id}")