import requests
from django.conf import settings


def send_order(order):
    """
    MILAN 거래처 주문 요청 (데모 API)
    - 각 OrderItem에서 옵션별 바코드, 수량, 사이즈 추출
    - 데모 API: http://lab.modacheva.com/demo_getorder
    """
    endpoint = "http://lab.modacheva.com/demo_getorder"  # 운영 시 교체 가능

    results = []

    for item in order.items.all():
        option = item.option

        payload = {
            "Barcode": option.external_option_id,     # 옵션 바코드
            "Qty": item.quantity,                     # 주문 수량
            "Size": option.option_name,               # 사이즈
            "Order": f"ORDER-{order.id}-{item.id}"    # 주문번호 (중복불가 조건 대비)
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
