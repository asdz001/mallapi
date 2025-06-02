import requests
import json
import traceback
from django.conf import settings


API_URL = "https://www2.atelier-hub.com/hub/CreateNewOrder"
USER_MKT = "MILANESEKOREA"
PWD_MKT = "4RDf55<lwja*"

HEADERS = {
    "Content-Type": "application/json",
    "USER_MKT": USER_MKT,
    "PWD_MKT": PWD_MKT,
    "LANGUAGE": "en"
}

# ✅ 테스트 모드 여부 (True면 전송 없이 출력만 함)
TEST_MODE = False


def send_order(order):
    """
    아뜰리에 API로 주문 전송
    """
    goods = []

    print(f"\n🧾 주문번호: {order.id}")
    print(f"🛍️ 거래처: {order.retailer.name} / 코드: {order.retailer.code}")

    for item in order.items.all():
        option = item.option
        print(f"📦 상품명: {item.product.product_name}")
        print(f"   옵션명: {option.option_name}")
        print(f"   바코드: {option.external_option_id}")
        print(f"   수량: {item.quantity}")
        print(f"   원가(price_org): {item.product.price_org}")
        print(f"   통화: EUR")

        goods.append({
            "ID": option.external_option_id,
            "Size": option.option_name,
            "Qty": item.quantity,
            "Price": str(item.product.price_org),
            "Currency": "EUR",
            "ReferencePrice": ""
        })

    item = order.items.first()
    if item:
        date_str = order.created_at.strftime("%Y%m%d")
        retailer_code = order.retailer.code.replace("IT-", "").replace("-", "")
        order_reference = f"{date_str}-ORDER-{order.id}-{item.id}-{retailer_code}"
    else:
        order_reference = f"ORDER-{order.id}"

    retailer_name = order.retailer.order_api_name or order.retailer.name

    payload = {
        "OrderId": order_reference,
        "Retailer": retailer_name,
        "StockPointId": "",
        "BuyerInfo": {
            "Name": "MILANESE KOREA",
            "Address": "F1025 MISACENTUMBIZ, 45 JOJUNGDAE-RO",
            "ZipCode": "12918",
            "City": "HANAM-SI",
            "PhoneNumber": "01073360902",
            "Email": "md@milanese.co.kr",
            "ISOcountry": "KR",
            "TypeShipping": "Logistic"
        },
        "GoodsList": {
            "Good": goods
        }
    }

    try:
        # 🧪 테스트 모드: 전송 없이 출력
        print("\n📤 전송 Payload:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        if TEST_MODE:
            return [{
                "success": None,
                "message": "[테스트 모드] 전송 안 함. Payload만 출력"
            }]

        # 🛰️ 실전 전송
        response = requests.post(API_URL, json=payload, headers=HEADERS)
        print(f"📨 응답 코드: {response.status_code}")
        print("📨 응답 본문:", response.text)

        response.raise_for_status()
        result = response.json().get("Response", {})

        print("✅ 아뜰리에 응답:", result)

        return [{
            "success": result.get("Result") == "Success",
            "message": result.get("Message", "")
        }]

    except Exception as e:
        print("❌ [아뜰리에 오류]", str(e))
        traceback.print_exc()
        return [{
            "success": False,
            "message": str(e)
        }]
