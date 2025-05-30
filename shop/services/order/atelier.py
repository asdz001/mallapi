import requests
import json
import traceback
from requests.auth import HTTPBasicAuth

# 운영 서버 API URL
API_URL = "https://www2.atelier-hub.com/hub/CreateNewOrder"

# 운영 계정 인증 정보
USER_ID = "Marketplace2"
USER_PW = "@aghA87plJ1,"
USER_MKT = "MILANESEKOREA"
PWD_MKT = "4RDf55<lwja*"

headers = {
    "Content-Type": "application/json",
    "USER_MKT": USER_MKT,
    "PWD_MKT": PWD_MKT,
    "LANGUAGE": "en"
}

TEST_MODE = False  # 운영 전환 시 False로 설정


def get_goods_id_by_barcode(barcode: str, size: str, retailer: str):
    """
    바코드와 사이즈로 유효성 검사 및 상품 ID 반환
    """
    try:
        print(f"\n🔍 유효성 검사 요청: barcode={barcode}, size={size}, retailer={retailer}")
        response = requests.get(
            "https://www2.atelier-hub.com/hub/GoodsDetailList",
            headers={
                "USER_MKT": USER_MKT,
                "PWD_MKT": PWD_MKT,
                "LANGUAGE": "en",
                "DESCRIPTION": "ALL",
                "SIZEPRICE": "ON",
                "DETAILEDSIZE": "ON"
            },
            auth=HTTPBasicAuth(USER_ID, USER_PW),
            params={"retailer": retailer, "barcode": barcode}
        )
        print(f"🛰️ 응답 코드: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        print(f"📦 응답 데이터:\n{json.dumps(data, indent=2)}")

        goods = data.get("GoodsDetailList", {}).get("Good", [])
        if not goods:
            print(f"❌ 바코드 {barcode}에 해당하는 상품 없음")
            return None

        for stock in goods[0].get("Stock", {}).get("Item", []):
            found_size = stock.get("Size", "").strip().upper()
            if found_size == size.strip().upper():
                print(f"✅ 유효한 사이즈 매칭: {size}")
                return goods[0].get("ID")  # 상품 ID 반환

        print(f"❌ 사이즈 {size} 없음")
        return None

    except Exception as e:
        print(f"❌ 유효성 검사 실패: {e}")
        traceback.print_exc()
        return None


def send_order(order):
    goods = []

    print(f"\n🧾 주문번호: {order.id}")
    print(f"🛍️ 거래처: {order.retailer.name} / 코드: {order.retailer.code}")

    retailer_name = order.retailer.order_api_name or order.retailer.name

    for item in order.items.all():
        option = item.option
        barcode = option.external_option_id
        size = option.option_name

        print(f"📦 상품명: {item.product.product_name}")
        print(f"   옵션명: {size}")
        print(f"   바코드: {barcode}")
        print(f"   수량: {item.quantity}")
        print(f"   원가(price_org): {item.product.price_org}")
        print(f"   통화: EUR")

        # ✅ 유효성 검사 + 상품 ID 추출
        goods_id = get_goods_id_by_barcode(barcode, size, retailer_name)
        if not goods_id:
            print(f"⚠️ 제외됨: 바코드 {barcode} - 사이즈 {size}")
            continue

        price_str = str(item.product.price_org).replace('.', ',')

        goods.append({
            "ID": goods_id,  # ✅ 상품 ID 사용
            "Size": size,
            "Qty": item.quantity,
            "Price": price_str,
            "Currency": "EUR",
            "ReferencePrice": ""
        })

    if not goods:
        print("❌ 유효한 주문 항목이 없어 전송 중단")
        return [{
            "success": False,
            "message": "유효한 옵션 없음"
        }]

    item = order.items.first()
    date_str = order.created_at.strftime("%Y%m%d")
    retailer_code = order.retailer.code.replace("IT-", "").replace("-", "")
    order_reference = f"{date_str}-ORDER-{order.id}-{item.id}-{retailer_code}"

    payload = {
        "USER_MKT": USER_MKT,
        "PWD_MKT": PWD_MKT,
        "LANGUAGE": "en",
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
        print("\n📤 전송 Payload:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        if TEST_MODE:
            print("⚠️ 테스트 모드로 실제 전송 안 함")
            return [{
                "success": None,
                "message": "[테스트 모드] 전송 안 함"
            }]

        response = requests.post(
            API_URL,
            json=payload,
            headers=headers,
            auth=HTTPBasicAuth(USER_ID, USER_PW)
        )
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
        print("❌ [아뜰리에 오류 발생]")
        print("❗ 오류 메시지:", str(e))
        traceback.print_exc()
        return [{
            "success": False,
            "message": str(e)
        }]
