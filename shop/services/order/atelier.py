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

        # ✅ 응답 구조 확인
        if not isinstance(data, dict):
            print("❌ 응답이 JSON 객체가 아님! → 서버가 에러를 반환한 것으로 판단")
            return None

        goods = data.get("GoodsDetailList", {}).get("Good", [])
        if not goods:
            print(f"❌ 바코드 {barcode}에 해당하는 상품 없음")
            return None

        for stock in goods[0].get("Stock", {}).get("Item", []):
            found_size = stock.get("Size", "").strip().upper()
            if found_size == size.strip().upper():
                print(f"✅ 유효한 사이즈 매칭: {size}")
                return goods[0].get("ID")

        print(f"❌ 사이즈 {size} 없음")
        return None

    except Exception as e:
        print(f"❌ 유효성 검사 실패: {e}")
        traceback.print_exc()
        return None

    


def send_order(order):
    goods = []
    results = []

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
            results.append({
                "sku": barcode,
                "item_id": item.id,  # 주문 항목 고유 ID
                "success": False,
                "reason": f"유효하지 않은 옵션: {barcode} / {size}"
            })
            continue

        price_str = str(item.product.price_org).replace('.', ',')

        goods.append({
            "ID": goods_id,
            "Size": size,
            "Qty": item.quantity,
            "Price": price_str,
            "Currency": "EUR",
            "ReferencePrice": ""
        })

        results.append({
            "sku": barcode,
            "item_id": item.id,  # 주문 항목 고유 ID
            "success": True,
            "reason": ""
        })

    if not goods:
        print("❌ 유효한 주문 항목이 없어 전송 중단")
        return results

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
        print("\n📡 아뜰리에 주문 전송 중...")
        response = requests.post(API_URL, headers=headers, json=payload, auth=HTTPBasicAuth(USER_ID, USER_PW))
        print(f"📥 응답 코드: {response.status_code}")
        print("📥 응답 본문:", response.text)

        response.raise_for_status()

        # ✅ 응답 타입 검사
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError("응답이 JSON 객체가 아님")

        response_data = result.get("Response", {})
        if not isinstance(response_data, dict):
            raise ValueError("응답 내 Response 구조가 없음")

        if response_data.get("Result") != "Success":
            message = response_data.get("Message", "전송 실패")
            for r in results:
                if r["success"]:
                    r["success"] = False
                    r["reason"] = message

    except Exception as e:
        print("❌ 전송 중 예외 발생:", e)
        traceback.print_exc()
        for r in results:
            if r["success"]:
                r["success"] = False
                r["reason"] = str(e)

    # ✅ 모든 결과에 sku 포함 여부 최종 체크
    complete_results = []
    for item in order.items.all():
        barcode = item.option.external_option_id
        result = next((r for r in results if r["sku"] == barcode), None)
        if result:
            complete_results.append(result)
        else:
            complete_results.append({
                "sku": barcode,
                "item_id": item.id,  # 주문 항목 고유 ID
                "success": False,
                "reason": "결과 누락 또는 처리되지 않음"
            })

    return complete_results




