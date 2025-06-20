import requests
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from shop.models import Order
from utils.order_logger import log_order_send

#BASE_URL = "https://sandbox.csplatform.io:9950" #테스트 주소
BASE_URL = "https://api.csplatform.io"
ORDER_ENDPOINT = f"{BASE_URL}/shop/v1/orders"
#TOKEN = "61a61031e8107c472fc312f3-66013c37f598544a853a23fd:5d630d9844a6d0827d14247d6cafeec0" #테스트 토큰
TOKEN = '61a61031e8107c472fc312f3-6791f518791ad1287012b863:b151b2e915b67e6bbafd22e230f959bb'
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# ✅ 옵션 ID와 SKU 매핑을 최신 JSON 파일에서 로드
def load_optionid_to_sku_map_from_latest_json():
    folder = Path("export/BASEBLU")
    json_files = sorted(folder.glob("base_blu_raw_*.json"), reverse=True)
    if not json_files:
        print("❌ base_blu_raw_*.json 파일이 없습니다.")
        return {}

    latest_json = json_files[0]
    print(f"📁 최신 JSON 파일 로드: {latest_json}")

    sku_map = {}
    with open(latest_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for item in data:
            sku = item.get("sku")
            item_id = item.get("item_id", {}).get("$oid")
            if item_id and sku:
                sku_map[item_id] = {"sku": sku, "item_id": item_id}
    return sku_map

# ✅ 실시간 API 호출로 SKU 조회
def fetch_sku_from_api(option_id):
    try:
        url = f"{BASE_URL}/shop/v1/items/{option_id}"
        res = requests.get(url, headers=HEADERS, timeout=5)
        res.raise_for_status()
        data = res.json()
        sku = data.get("sku")
        if sku:
            print(f"✅ 실시간 조회 성공 → option_id={option_id}, sku={sku}")
            return {"sku": sku, "item_id": option_id}
        else:
            print(f"❌ SKU 없음 → option_id={option_id}")
            return None
    except Exception as e:
        print(f"❌ 실시간 SKU 조회 실패 → option_id={option_id} / {e}")
        return None


# ✅ 통합 조회 함수: JSON + 실시간 fallback
def get_sku_info(option_id, sku_map):
    info = sku_map.get(option_id)
    if info:
        return info
    return fetch_sku_from_api(option_id)


# ✅ 주문 전송 함수
def send_order(order: Order):
    print(f"\n🛰️ [API 전송 시작] 주문번호: {order.id}, 거래처: BASEBLU")
    sku_map = load_optionid_to_sku_map_from_latest_json()

    items = []
    results = []

    total_qty = 0
    total_amount = Decimal("0.00")

    for item in order.items.all():
        option_id = item.option.external_option_id
        info = get_sku_info(option_id, sku_map)
        sku = info.get("sku", "-") if info else "-"

        qty = item.quantity
        price = item.product.price_org or Decimal("0.00")

        unit_price_tax_excl = price
        unit_price_tax = Decimal("0.00")
        unit_price_tax_incl = unit_price_tax_excl + unit_price_tax
        total_price_tax_incl = unit_price_tax_incl * qty
        total_price_tax_excl = unit_price_tax_excl * qty
        total_price_tax = unit_price_tax * qty

        total_qty += qty
        total_amount += total_price_tax_incl

        print(f"📦 상품명: {item.product.product_name}")
        print(f"   옵션ID(item_id): {option_id}")
        print(f"   수량: {qty}")
        print(f"   원가(price_org): {price}")
        print(f"   통화: EUR")

        items.append({
            "item_id": {"$oid": option_id},
            "sku": sku,
            "qty": qty,
            "price": float(total_price_tax_incl),
            "unit_price_tax_excl": {"amount": float(unit_price_tax_excl), "currency": "EUR"},
            "unit_price_tax": {"amount": float(unit_price_tax), "currency": "EUR"},
            "unit_price_tax_incl": {"amount": float(unit_price_tax_incl), "currency": "EUR"},
            "total_price_tax_excl": {"amount": float(total_price_tax_excl), "currency": "EUR"},
            "total_price_tax": {"amount": float(total_price_tax), "currency": "EUR"},
            "total_price_tax_incl": {"amount": float(total_price_tax_incl), "currency": "EUR"}
        })

        # 결과 리스트에 항목 추가 (성공 여부는 후처리)
        results.append({
            "sku": option_id,
            "item_id": item.id,
            "success": True,
            "reason": ""
        })


    shop_order_id = item.external_order_number
 

    order_dt = order.created_at.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace("+00:00", "Z")

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

    payload = {
        "order": {
            "shop_order_id": shop_order_id,
            "order_status": "CONFIRMED",
            "order_dt": {"$date": order_dt},
            "buyer_identifier": "MILAEX00",
            "buyer_email": "md@milanese.co.kr",
            "buyer_name": "JD CHO",
            "billing_info": {
                "payment_method": "BANK_TRANSFER",
                "fiscal_code": "KR6178605369",
                "address": address_info
            },
            "shipping_info": {
                "address": address_info
            },
            "items": items
        }
    }

    try:
        print("📤 전송 Payload:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        response = requests.post(ORDER_ENDPOINT, json=payload, headers=HEADERS, timeout=10)
        print(f"📨 응답 코드: {response.status_code}")
        print("📨 응답 본문:", response.text)
        response.raise_for_status()

        # ✅ 성공 로그
        log_order_send(
            order_id=order.id,
            retailer_name="BASEBLU",
            items=[{"sku": r["sku"], "quantity": order.items.get(id=r["item_id"]).quantity} for r in results],
            success=True
        )        

        # 성공일 경우에도 result 리턴만 함 (order 저장 X)
        return results

    except Exception as e:
        error_message = str(e)
        print("❌ 전송 실패:", error_message)

        is_stock_missing = "ITEM_NOT_FOUND" in error_message.upper()        

        # 결과 항목의 success = False, reason에 오류 메시지 기입
        for r in results:
            r["success"] = False
            r["reason"] = "재고 없음" if is_stock_missing else f"바제블루 전송 실패: {error_message}"

        # ✅ 각 항목 상태 업데이트
        for r in results:
            try:
                item = order.items.get(id=r["item_id"])
                if is_stock_missing:
                    item.order_status = "SOLDOUT"
                    item.order_message = r["reason"]
                else:
                    item.order_status = "FAILED"
                    item.order_message = r["reason"]
                item.save()
            except Exception as e2:
                print(f"⚠️ 항목 상태 업데이트 실패 (item_id={r['item_id']}):", e2)


        # ✅ 실패 로그
        log_order_send(
            order_id=order.id,
            retailer_name="BASEBLU",
            items=[{"sku": r["sku"], "quantity": order.items.get(id=r["item_id"]).quantity} for r in results],
            success=False,
            reason=error_message
        )

        
        return results
