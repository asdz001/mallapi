import requests
import json
import traceback
from requests.auth import HTTPBasicAuth
from utils.order_logger import log_order_send

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

        price_str = str(item.product.price_org).replace('.', ',')

        goods.append({
            "ID": item.product.external_product_id or "",
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



    item = order.items.first()
    order_reference = item.external_order_number

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

    # ✅ 실제 전송 대신 payload만 출력
    print("\n🚫 실제 전송은 생략하고 전송될 데이터만 출력합니다:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    try:
        print("\n📡 아뜰리에 주문 전송 중...")
        response = requests.post(API_URL, headers=headers, json=payload, auth=HTTPBasicAuth(USER_ID, USER_PW))
        print(f"📥 응답 코드: {response.status_code}")
        print("📥 응답 본문:", response.text)

        response.raise_for_status()
        result = response.json()

        response_data = result.get("Response", {})
        if response_data.get("Result") != "Success":
            message = response_data.get("Message", "전송 실패")

            for r in results:
                r["success"] = False
                if "not enough stock" in message.lower():
                    r["reason"] = "품절"
                    r["status"] = "SOLDOUT"
                else:
                    r["reason"] = message
                    r["status"] = "FAILED"

    except Exception as e:
        print("❌ 전송 중 예외 발생:", e)
        traceback.print_exc()

    # ✅ 주문 항목 상태 업데이트
    for r in results:
        item = order.items.get(id=r["item_id"])
        if r.get("status") == "SOLDOUT":
            item.order_status = "SOLDOUT"
            item.order_message = r["reason"]
        elif not r["success"]:
            item.order_status = "FAILED"
            item.order_message = r["reason"]
        else:
            item.order_status = "SENT"
            item.order_message = ""
        item.save()


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


    items = []
    for r in complete_results:
        item_obj = order.items.get(id=r["item_id"])
        items.append({
            "sku": item_obj.option.external_option_id,
            "size": item_obj.option.option_name,
            "product_id": item_obj.product.external_product_id,  # ✅ 고유 ID 추가
            "quantity": item_obj.quantity
        })

    log_order_send(
        order_id=order.id,
        retailer_name=order.retailer.name,
        items=items,
        success=all(r["success"] for r in complete_results),
        reason="일부 실패" if any(not r["success"] for r in complete_results) else "",
        payload=payload,
        response=response.text if 'response' in locals() else None,
        error=str(e) if 'e' in locals() else None
    )

    return complete_results




