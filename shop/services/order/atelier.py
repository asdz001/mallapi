def send_order(order):
    """
    아뜰리에 API로 주문 전송
    """
    goods = []
    for item in order.items.all():
        option = item.option

        # ✅ 주문용 바코드(ID), 사이즈, 수량, 가격, 통화
        goods.append({
            "ID": option.external_option_id,
            "Size": option.option_name,
            "Qty": item.quantity,
            "Price": str(item.product.price_org),  # ✅ VAT 제외 원가
            "Currency": "EUR",                     # ✅ 유로
            "ReferencePrice": ""                   # 생략 가능
        })

    # ✅ order_reference 생성 (admin에서도 동일 형식 사용)
    item = order.items.first()
    if item:
        date_str = order.created_at.strftime("%Y%m%d")
        retailer_code = order.retailer.code.replace("IT-", "").replace("-", "")
        order_reference = f"{date_str}-ORDER-{order.id}-{item.id}-{retailer_code}"
    else:
        order_reference = f"ORDER-{order.id}"

    # ✅ API용 리테일러 이름
    retailer_name = order.retailer.order_api_name or order.retailer.name

    payload = {
        "OrderId": order_reference,
        "Retailer": retailer_name,
        "StockPointId": "",  # 필요 시 추후 연결
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
        response = requests.post(API_URL, json=payload, headers=HEADERS)
        response.raise_for_status()
        result = response.json().get("Response", {})

        print("📨 [아뜰리에 응답]", result)

        return [{
            "success": result.get("Result") == "Success",
            "message": result.get("Message", "")
        }]
    except Exception as e:
        print("❌ [아뜰리에 오류]", str(e))
        return [{
            "success": False,
            "message": str(e)
        }]
