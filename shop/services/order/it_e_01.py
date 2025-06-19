import requests
import json
from datetime import datetime
from utils.order_logger import log_order_send

PERSONAL_CODE = "da3e1b50-8ce1-433d-a7a5-6353b0c969d3"
ORDER_INPUT_URL = "https://order.eleonorabonucci.com/ws/order.asmx/Order_Input"
ORDER_ADDRESS_URL = "https://api.eleonorabonucci.com/API/Order/Insert/Address"

def send_order(order):
    """
    엘레오노라 주문 전송
    Returns:
        list: [{"sku": 바코드, "item_id": 주문항목ID, "success": bool, "reason": str}]
    """

    item = order.items.first()
    reference = item.external_order_number


    print("🧾 주문 전송 시작 →", reference)

    basket = []
    item_map = {}  # SKU_item → item
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

        response_map = {}
        for entry in result1.get("SKU_item", []):
            sku = entry.get("SKU_item")
            qty_added = entry.get("Qty_added", 0)
            item = item_map.get(sku)
            if not item:
                continue
            response_map[sku] = {
                "item_id": item.id,
                "success": qty_added > 0
            }

    except Exception as e:
        print("❌ Step 1 실패:", e)


        log_order_send(
            order_id=order.id,
            retailer_name="ELEONORA",
            items=[{"sku": item.option.external_option_id, "quantity": item.quantity} for item in order.items.all()],
            success=False,
            reason=str(e)
        )
        
        return [
            {
                "sku": item.option.external_option_id,
                "item_id": item.id,
                "success": False,
                "reason": str(e)
            }
            for item in order.items.all()
        ]
    

    # ✅ Step 2: 주소 정보 전송
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
        headers = {"Authorization": f"Bearer {PERSONAL_CODE}"}
        print("📤 요청 Payload:")
        print(json.dumps(address_payload, indent=2))

        res2 = requests.post(ORDER_ADDRESS_URL, headers=headers, json=address_payload)
        res2.raise_for_status()

        result2 = res2.json() if res2.headers.get("Content-Type") == "application/json" else res2.text

        if isinstance(result2, dict) and result2.get("Success") is not True:
            raise Exception("주소 정보 전송 실패")

    except Exception as e:
        print("❌ Step 2 예외 발생:", e)

        log_order_send(
            order_id=order.id,
            retailer_name="ELEONORA",
            items=[{"sku": sku, "quantity": order.items.get(option__external_option_id=sku).quantity} for sku in response_map.keys()],
            success=False,
            reason=f"주소 전송 실패: {str(e)}"
        )

        return [
            {
                "sku": sku,
                "item_id": data["item_id"],
                "success": False,
                "reason": f"주소 전송 실패: {str(e)}"
            }
            for sku, data in response_map.items()
        ]
    
    log_order_send(
        order_id=order.id,
        retailer_name="ELEONORA",
        items=[
            {"sku": sku, "quantity": order.items.get(option__external_option_id=sku).quantity}
            for sku, data in response_map.items()
        ],
        success=all(data["success"] for data in response_map.values()),
        reason="일부 실패" if any(not data["success"] for data in response_map.values()) else ""
    )


    # ✅ 최종 표준 응답 반환
    return [
        {
            "sku": sku,
            "item_id": data["item_id"],
            "success": data["success"],
            "reason": "" if data["success"] else "재고 없음"
        }
        for sku, data in response_map.items()
    ]
