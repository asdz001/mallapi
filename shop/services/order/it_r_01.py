import requests
from django.conf import settings
from datetime import datetime


def send_order(order):
    """
    MILAN 거래처 주문 요청 (데모 API)
    - 각 OrderItem에서 옵션별 바코드, 수량, 사이즈 추출
    - 데모 API: http://lab.modacheva.com/demo_getorder
    """
    endpoint = "https://lab.modacheva.com/mil_getorder"  # 운영 시 교체 가능

    results = []

    for item in order.items.all():
        option = item.option
        retailer_code = order.retailer.code.replace("IT-", "").replace("-", "")  # "R01"
        order_date = order.created_at.strftime("%Y%m%d")  # "20250526"

        order_code = f"{order_date}-ORDER-{order.id}-{item.id}-{retailer_code}"

        payload = {
            "Barcode": option.external_option_id,     # 옵션 바코드
            "Qty": item.quantity,                     # 주문 수량
            "Size": option.option_name,               # 사이즈
            "Order": order_code  # ✅ 여기에 주문번호 반영
        }

        # ✅ 디버깅용 로그 출력
        print(f"📤 전송 Payload: {payload}")

        try:
            response = requests.post(endpoint, data=payload, timeout=10)
            response.raise_for_status()

            results.append({
                "option": option.option_name,
                "response": response.text,
                "success": True
            })
            print(f"📬 응답: {response.text}")

        except requests.RequestException as e:
            results.append({
                "option": option.option_name,
                "response": str(e),
                "success": False
            })

    return results
