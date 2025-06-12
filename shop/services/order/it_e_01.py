import requests
import json
from shop.models import Order
from datetime import datetime

# ✅ 설정값 (실제 API KEY는 환경변수나 DB에서 불러오는 구조로 대체 가능)
PERSONAL_CODE = "9d82bdbb-2636-4791-b445-353a26a87f2f"
ORDER_INPUT_URL = "https://order.eleonorabonucci.com/ws/order.asmx/Order_Input"
ORDER_ADDRESS_URL = "https://api.eleonorabonucci.com/API/Order/Insert/Address"


def send_order(order: Order):
    """
    엘레오노라(IT-E-01) 주문 API 전송
    1단계: GET 방식 주문 (상품/수량/가격)
    2단계: POST 방식 주소 전송
    
    Returns:
        list: 성공 시 주문 아이템 리스트, 실패 시 빈 리스트
    """
    
    order_date = datetime.now().strftime("%Y%m%d")
    retailer_code = order.retailer.code.replace("IT-", "").replace("-", "")
    reference = f"{order_date}-ORDER-{order.id}-{order.items.first().id}-{retailer_code}"
    print("🧾 주문 전송 시작 →", reference)

    # ✅ 장바구니 아이템 구성
    basket = []
    item_map = {}  # SKU_item -> order item
    for item in order.items.all():
        option = item.option
        sku_item = option.external_option_id
        basket.append({
            "SKU_item": sku_item,
            "Qty": item.quantity,
            "Price": float(option.price)
        })
        item_map[sku_item] = item

    print(f"🧺 장바구니 항목 수: {len(basket)}개")
    print(json.dumps(basket, indent=2))

    # ✅ 1단계: 주문 전송
    order_input_payload = {
        "Personal_Code": PERSONAL_CODE,
        "Reference": reference,
        "Basket": basket
    }

    try:
        print("📡 Step 1: ORDER_INPUT 호출 중...")
        res1 = requests.get(ORDER_INPUT_URL, params={"json": json.dumps(order_input_payload)})
        res1.raise_for_status()
        result1 = res1.json()
        print("✅ Step 1 완료 응답:")
        print(json.dumps(result1, indent=2))

        # ✅ 응답 내 Qty_added 확인
        failed_items = []
        for entry in result1.get("SKU_item", []):
            if entry.get("Qty_added", 0) <= 0:
                failed_items.append(entry.get("SKU_item"))

        if failed_items:
            raise Exception(f"재고 부족 또는 실패 항목: {failed_items}")

    except Exception as e:
        print("❌ Step 1 실패:", e)   
        return []  # 빈 리스트 반환

    # ✅ 2단계: 주소 정보 전송 - address_info 기반 가공
    address_info = {
        "last_name": "CHO",
        "first_name": "JD",
        "company_name": "MILANESE KOREA CO LTD",
        "street": "JOJUNGDAE-RO",
        "house_number": "F1025, 45",
        "zip": "12918",
        "city": "HANAM-SI",
        "province": "GYEONGGI-DO"
    }

    address_payload = {
        "Reference": reference,
        "Billing": {
            "Name": f"{address_info['first_name']} {address_info['last_name']}",
            "Email": "md@milanese.co.kr",
            "Phone": "01073360902",
            "Address": f"{address_info['street']} {address_info['house_number']}, {address_info['province']}",
            "Zip": address_info["zip"],
            "City": address_info["city"],
            "Country": "South Korea",
            "CountryCode": "KR"
        },
        "Shipping": {
            "Name": f"{address_info['first_name']} {address_info['last_name']}",
            "Email": "md@milanese.co.kr",
            "Phone": "01073360902",
            "Address": f"{address_info['street']} {address_info['house_number']}, {address_info['province']}",
            "Zip": address_info["zip"],
            "City": address_info["city"],
            "Country": "South Korea",
            "CountryCode": "KR"
        },
        "Items": [
            {
                "Sku": item.option.external_option_id,
                "Quantity": item.quantity,
                "Price": float(item.option.price)
            } for item in order.items.all()
        ]
    }

    try:
        print("📡 Step 2: ORDER_ADDRESS 호출 중...")
        # 🔧 핵심 수정: 로그에서 확인된 성공 방식 사용
        headers = {"Authorization": PERSONAL_CODE}  # Bearer 제거!
        print("📤 요청 Payload:")
        print(json.dumps(address_payload, indent=2))

        res2 = requests.post(ORDER_ADDRESS_URL, headers=headers, json=address_payload)
        res2.raise_for_status()

        print("📥 응답 status_code:", res2.status_code)
        print("📥 응답 Content-Type:", res2.headers.get("Content-Type"))
        print("📥 응답 raw text:")
        print(res2.text)

        try:
            result2 = res2.json()
            print("📥 res2.json() 파싱 성공!")
            print("📥 result2 타입:", type(result2))
        except Exception as json_error:
            print("❌ res2.json() 파싱 실패:", json_error)
            result2 = res2.text

        # 🔧 핵심 수정: 매뉴얼에 따른 정확한 성공 판정
        if isinstance(result2, dict):
            print("✅ Step 2 응답 (dict):")
            print(json.dumps(result2, indent=2))
            
            # 매뉴얼에 따른 성공 확인: {"Success": true}
            if result2.get("Success") is True:
                print("🎉 주문 전송 완료!")
                # 성공 시 주문 아이템 정보 반환
                return [{"order_id": order.id, "reference": reference, "success": True}]
            else:
                print("❌ API 응답에서 Success가 true가 아님")
                return []
                
        elif isinstance(result2, bool):
            print(f"✅ Step 2 응답 (bool): {result2}")
            if result2:
                print("🎉 주문 전송 완료!")
                return [{"order_id": order.id, "reference": reference, "success": True}]
            else:
                print("❌ EB 응답이 False → 실패 처리")
                return []
        else:
            print(f"⚠️ Step 2 응답이 예상 외 타입입니다: {type(result2)} → {result2}")
            # 200 응답이고 에러가 없으면 성공으로 처리
            if res2.status_code == 200:
                print("🎉 주문 전송 완료!")
                return [{"order_id": order.id, "reference": reference, "success": True}]
            else:
                return []

    except Exception as e:
        print("❌ Step 2 예외 발생:", e)
        return []

    # 이 라인은 실행되지 않지만 안전을 위해 유지
    print("🎉 주문 전송 완료!")
    return [{"order_id": order.id, "reference": reference, "success": True}]