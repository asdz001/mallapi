import requests
import pandas as pd
import os
import json
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed

# 거래처 정보
RETAILER = "BINI"
BASE_PATH = os.path.join("export", RETAILER)
EXPORT_JSON = os.path.join(BASE_PATH, f"{RETAILER}_goods.json")
TIMESTAMP_PATH = os.path.join(BASE_PATH, "last_goodslist_timestamp.txt")

# 인증 정보
USER_ID = "Marketplace2"
USER_PW = "@aghA87plJ1,"
USER_MKT = "MILANESEKOREA"
PWD_MKT = "4RDf55<lwja*"

BASE_URL = "https://www2.atelier-hub.com/hub/"
HEADERS = {
    "USER_MKT": USER_MKT,
    "PWD_MKT": PWD_MKT,
    "LANGUAGE": "en",
    "DESCRIPTION": "ALL",
    "SIZEPRICE": "ON",
    "DETAILEDSIZE": "ON"
}

MAX_PAGES = 300
PAGE_SIZE = 100
WORKERS = 20

def fetch_page(page, timestamp=None):
    url = f"{BASE_URL}GoodsList"
    params = {
        "pageNum": page,
        "pageSize": PAGE_SIZE,
        "retailer": RETAILER.upper(),
    }
    if timestamp:
        params["modifiedTimestamp"] = timestamp

    try:
        res = requests.get(
            url,
            headers=HEADERS,
            params=params,
            auth=HTTPBasicAuth(USER_ID, USER_PW),
            timeout=30,
        )

        if res.status_code != 200:
            print(f"❌ Page {page} - 요청 실패 (status {res.status_code})")
            return page, []

        data = res.json()
        goods = data.get("GoodsList", {}).get("Good", [])
        print(f"📦 Page {page} - {len(goods)}개 수집됨")
        return page, goods

    except Exception as e:
        print(f"❌ Page {page} - 예외 발생: {e}")
        return page, []

def fetch_goods_list_BINI():
    print("🕒 BINI 전체 상품 수집 시작...")
    all_goods = {}
    last_timestamp = None

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(fetch_page, page, last_timestamp): page for page in range(1, MAX_PAGES + 1)}

        for future in as_completed(futures):
            page, result = future.result()
            if result:
                all_goods[page] = result

    # 정렬된 순서로 합치기
    merged_goods = []
    sorted_pages = sorted(all_goods.keys())
    for p in sorted_pages:
        merged_goods.extend(all_goods[p])

        # 종료 조건:
        if len(all_goods[p]) < PAGE_SIZE:
            next_page = p + 1
            if next_page not in all_goods or len(all_goods.get(next_page, [])) == 0:
                print(f"🛑 조건 충족 - Page {p}는 100개 미만이고, Page {next_page}는 없음 → 종료")
                break

    df = pd.DataFrame(merged_goods)

    # 비니실비아 전용 조건: 재고 필터링
    if "InStock" in df.columns:
        df["InStock"] = pd.to_numeric(df["InStock"], errors="coerce").fillna(0)
        df = df[df["InStock"] > 0]

    os.makedirs(BASE_PATH, exist_ok=True)
    goods_list = df.to_dict(orient="records")
    with open(EXPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(goods_list, f, ensure_ascii=False, indent=2)

    print(f"✅ 최종 수집 상품 수: {len(goods_list)}개")
    print(f"📄 저장 위치: {EXPORT_JSON}")

    with open(os.path.join(BASE_PATH, f"{RETAILER}_goods.done"), "w") as f:
        f.write("done")

if __name__ == "__main__":
    fetch_goods_list_BINI()
