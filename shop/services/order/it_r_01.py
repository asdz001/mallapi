import requests
from datetime import datetime
from shop.models import Order
from utils.order_logger import log_order_send

def send_order(order: Order):
    """
    라띠(LATTI) API 주문 전송
    Returns:
        list: [{"sku": 바코드, "success": bool, "reason": 실패 사유}]
    """
    endpoint = "https://lab.modacheva.com/mil_getorder"  # 운영 시 교체 가능
    results = []

    for item in order.items.all():
        option = item.option
        barcode = option.external_option_id
        size = option.option_name
        qty = item.quantity

        order_code = item.external_order_number

        payload = {
            "Barcode": barcode,
            "Qty": qty,
            "Size": size,
            "Order": order_code
        }

        print(f"📤 전송 Payload: {payload}")

        try:
            response = requests.post(endpoint, data=payload, timeout=10)
            response.raise_for_status()
            response_text = response.text.strip()

            print(f"📬 응답: {response_text}")

            # 성공 여부 판별: 단순 문자열 비교
            is_success = "OK" in response_text.upper()

            results.append({
                "sku": barcode,
                "item_id": item.id,
                "success": is_success,
                "reason": "" if is_success else response_text
            })

        except Exception as e:
            print(f"❌ 예외 발생: {str(e)}")
            results.append({
                "sku": barcode,
                "item_id": item.id,
                "success": False,
                "reason": str(e)
            })

    log_order_send(
        order_id=order.id,
        retailer_name="LATTI",
        items=[
            {
                "sku": r["sku"],
                "quantity": order.items.get(id=r["item_id"]).quantity
            } for r in results
        ],
        success=all(r["success"] for r in results),
        reason="일부 실패" if any(not r["success"] for r in results) else ""
    )
            

    return results
