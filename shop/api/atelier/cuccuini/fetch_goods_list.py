import requests
import pandas as pd
import os
import json
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# 거래처 식별자
RETAILER = "CUCCUINI"
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


# 마지막 수집 시간 불러오기
def load_last_timestamp():
    if os.path.exists(TIMESTAMP_PATH):
        with open(TIMESTAMP_PATH, "r") as f:
            return f.read().strip()
    return None


# 현재 시간 저장
def save_current_timestamp():
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs(os.path.dirname(TIMESTAMP_PATH), exist_ok=True)
    with open(TIMESTAMP_PATH, "w") as f:
        f.write(now)


# 개별 페이지 수집
def fetch_page(page, timestamp=None):
    url = f"{BASE_URL}GoodsList"
    params = {
        "pageNum": page,
        "pageSize": PAGE_SIZE,
        "retailer": RETAILER.upper(),  # CUCCUINI 대문자로 필요할 경우
    }
    if timestamp:
        params["modifiedTimestamp"] = timestamp

    try:
        res = requests.get(
            url,
            headers=HEADERS,
            params=params,
            auth=HTTPBasicAuth(USER_ID, USER_PW),
            timeout=10,
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
def fetch_goods_list_CUCCUINI():
    all_goods = []
    last_timestamp = load_last_timestamp()

    print(f"🕒 이전 수집 시각: {last_timestamp if last_timestamp else '없음 (전체 수집)'}")

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
    if "InStock" in df.columns:
        df["InStock"] = pd.to_numeric(df["InStock"], errors="coerce").fillna(0)
        df = df[df["InStock"] > 0]

    # ✅ JSON 저장
    os.makedirs(BASE_PATH, exist_ok=True)
    goods_list = df.to_dict(orient="records")
    with open(EXPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(goods_list, f, ensure_ascii=False, indent=2)

    print(f"✅ 총 상품 수집 완료 (재고 있음): {len(goods_list)}개")
    print(f"📄 저장 파일: {EXPORT_JSON}")

    # 🔐 수집 시각 저장
    save_current_timestamp()


# 단독 실행용
if __name__ == "__main__":
    fetch_goods_list_CUCCUINI()
