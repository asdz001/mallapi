import requests
from datetime import datetime
from shop.models import Order


# 재고 조회 함수
def check_real_stock(barcode):
    try:
        url = f"https://app.modacheva.com/mil/bccodedispo/{barcode}"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        return int(data.get("stock", 0))
    except Exception as e:
        print(f"❌ 재고 조회 실패: {barcode} → {e}")
        return -1  # -1은 재고 조회 실패 의미
    


# 주문 전송 함수
def send_order(order: Order):
    """
    라띠(LATTI) API 주문 전송
    Returns:
        list: [{"sku": 바코드, "success": bool, "reason": 실패 사유}]
    """
    endpoint = "https://lab.modacheva.com/mil_getorder"  # 운영 시 교체 가능
    results = []
    payloads = []
    responses = []

    for item in order.items.all():
        option = item.option
        barcode = option.external_option_id
        size = option.option_name
        qty = item.quantity

        order_code = item.external_order_number

        # ✅ 재고 먼저 체크
        stock = check_real_stock(barcode)


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
            payloads.append(payload)
            responses.append(response_text)

            print(f"📬 응답: {response_text}")
            is_success = "OK" in response_text.upper()

            results.append({
                "sku": barcode,
                "item_id": item.id,
                "success": is_success,
                "reason": "" if is_success else response_text,
                "stock": stock
            })

        except Exception as e:
            print(f"❌ 예외 발생: {str(e)}")
            results.append({
                "sku": barcode,
                "item_id": item.id,
                "success": False,
                "reason": str(e),
                "stock": stock
            })
            payloads.append(payload)
            responses.append(str(e))


    for r in results:
        try:
            item = order.items.get(id=r["item_id"])
            stock = r.get("stock", -1)
            reason = r.get("reason", "")

            if r["success"]:
                item.order_status = "SENT"
                item.order_message = ""
            else:
                if stock == 0:
                    item.order_status = "SOLDOUT"
                    item.order_message = f"품절 ({reason})"
                else:
                    item.order_status = "FAILED"
                    item.order_message = reason

            item.save()
        except Exception as e:
            print(f"⚠️ 상태 저장 실패 (item_id={r['item_id']}) →", e)  


    return results, payloads, responses
