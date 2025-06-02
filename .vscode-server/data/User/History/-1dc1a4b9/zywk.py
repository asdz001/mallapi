import requests
import pandas as pd
import os
import json
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed


# 거래처 식별자
RETAILER = "MINETTI"
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

MAX_PAGES = 200
PAGE_SIZE = 100
WORKERS = 20


# 개별 페이지 수집
def fetch_page(page, timestamp=None):
    url = f"{BASE_URL}GoodsList"
    params = {
        "pageNum": page,
        "pageSize": PAGE_SIZE,
        "retailer": RETAILER.upper(),  # MINETTI 대문자로 필요할 경우
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
            return []

        data = res.json()
        goods = data.get("GoodsList", {}).get("Good", [])

        print(f"📦 Page {page} - {len(goods)}개 수집됨")
        return goods

    except Exception as e:
        print(f"❌ Page {page} - 예외 발생: {e}")
        return []


# 전체 수집 실행
def fetch_goods_list_MINETTI():
    all_goods = []
    last_timestamp = None

    print("🕒 MINETTI 전체 상품 수집 중...")

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(fetch_page, page, last_timestamp): page
            for page in range(1, MAX_PAGES + 1)
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                all_goods.extend(result)
            if result is not None and len(result) < PAGE_SIZE:
                print(f"🛑 마지막 페이지 도달 (Page {futures[future]})")
                break

    df = pd.DataFrame(all_goods)

    # ✅ 재고 0인 상품 제외
    #if "InStock" in df.columns:
        #df["InStock"] = pd.to_numeric(df["InStock"], errors="coerce").fillna(0)
        #df = df[df["InStock"] > 0]

    # ✅ JSON 저장
    os.makedirs(BASE_PATH, exist_ok=True)
    goods_list = df.to_dict(orient="records")
    with open(EXPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(goods_list, f, ensure_ascii=False, indent=2)

    print(f"✅ 총 상품 수집 완료 (재고 있음): {len(goods_list)}개")
    print(f"📄 저장 파일: {EXPORT_JSON}")

    with open("export/MINETTI/MINETTI_goods.done", "w") as f:
        f.write("done")


# 단독 실행용
if __name__ == "__main__":
    fetch_goods_list_MINETTI()
