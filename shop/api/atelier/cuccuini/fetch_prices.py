import pandas as pd
import requests
import json
import os
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed

# 설정값
RETAILER = "CUCCUINI"
RETAILER_UPPER = RETAILER.upper()
BASE_PATH = os.path.join("export", RETAILER)

INPUT_JSON = os.path.join(BASE_PATH, f"{RETAILER}_details.json")
OUTPUT_JSON = os.path.join(BASE_PATH, f"{RETAILER}_prices.json")
FAIL_LOG_PATH = os.path.join(BASE_PATH, f"{RETAILER}_price_failed.json")

MAX_WORKERS = 20
LIMIT = None  # None이면 전체 수집

# 인증 정보
USER_ID = "Marketplace2"
USER_PW = "@aghA87plJ1,"
USER_MKT = "MILANESEKOREA"
PWD_MKT = "4RDf55<lwja*"

HEADERS = {
    "USER_MKT": USER_MKT,
    "PWD_MKT": PWD_MKT,
    "LANGUAGE": "en",
    "SIZEPRICE": "ON"
}
BASE_URL = "https://www2.atelier-hub.com/hub/GoodsPriceList"

# ✅ 1. 단일 상품 가격 수집
def fetch_price_items(goods_id, options):
    result = []
    try:
        res = requests.get(
            BASE_URL,
            headers=HEADERS,
            params={"GoodsID": goods_id, "retailer": RETAILER_UPPER},
            auth=HTTPBasicAuth(USER_ID, USER_PW),
            timeout=10
        )
        if res.status_code != 200:
            return result, f"❌ Status {res.status_code}"

        data = res.json()
        groups = data.get("GoodsPriceList", {}).get("Price", [])
        if not groups:
            return result, "⚠️ Price 필드 없음"

        matched = False
        for group in groups:
            for retailer in group.get("Retailers", []):
                size_prices = retailer.get("SizePrices", [])
                net_price = retailer.get("NetPrice")
                brand_price = retailer.get("BrandReferencePrice")
                brand_price_exvat = retailer.get("BrandReferencePriceExVAT")
                discount = retailer.get("Discount")
                tax = retailer.get("PercentTax")
                currency = retailer.get("Currency")
                country = retailer.get("Country")

                # ✅ 매핑
                price_map = {
                    (item.get("Barcode"), item.get("Size")): item.get("SizeNetPrice")
                    for item in size_prices
                }

                for opt in options:
                    result.append({
                        "GoodsID": goods_id,
                        "Barcode": opt["Barcode"],
                        "Size": opt["Size"],
                        "Qty": opt["Qty"],
                        "SizeNetPrice": price_map.get((opt["Barcode"], opt["Size"])),
                        "NetPrice": net_price,
                        "BrandReferencePrice": brand_price,
                        "BrandReferencePriceExVAT": brand_price_exvat,
                        "Discount": discount,
                        "PercentTax": tax,
                        "Currency": currency,
                        "Country": country
                    })
                matched = True

        if not matched:
            return result, "⚠️ 가격 정보 없음 (SizePrices와 NetPrice 모두 없음)"
        return result, None

    except Exception as e:
        return [], f"❌ 예외 발생: {e}"

# ✅ 2. 전체 가격 수집
def fetch_all_prices():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        detail_data = json.load(f)

    grouped = {}
    for item in detail_data:
        gid = str(item.get("ID"))
        options = item.get("Sizes", [])
        if options:
            grouped[gid] = options

    if LIMIT:
        grouped = dict(list(grouped.items())[:LIMIT])

    print(f"📦 가격 수집 대상 상품 수: {len(grouped)}개 (limit={LIMIT})")

    all_results = []
    failed_logs = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_price_items, gid, options): gid
            for gid, options in grouped.items()
        }

        for i, future in enumerate(as_completed(futures), start=1):
            gid = futures[future]
            try:
                result, error = future.result()
                if result:
                    all_results.extend(result)
                    print(f"[{i}/{len(futures)}] ✅ GoodsID {gid} - 가격 {len(result)}개 수집됨")
                if error:
                    print(f"[{i}/{len(futures)}] ⚠️ GoodsID {gid} - 실패: {error}")
                    failed_logs[gid] = error
            except Exception as e:
                print(f"[{i}/{len(futures)}] ❌ GoodsID {gid} - 예외 발생: {e}")
                failed_logs[gid] = str(e)

    os.makedirs(BASE_PATH, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    with open(FAIL_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(failed_logs, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 가격 수집 완료: 옵션 총 {len(all_results)}개")
    print(f"❌ 실패 상품 수: {len(failed_logs)}개")
    print(f"📄 JSON 저장: {OUTPUT_JSON}")
    print(f"📄 실패 로그: {FAIL_LOG_PATH}")

if __name__ == "__main__":
    fetch_all_prices()
