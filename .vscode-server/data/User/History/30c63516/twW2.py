import requests
import json
from requests.auth import HTTPBasicAuth
from pathlib import Path

# 인증 정보
USER_ID = "Marketplace2"
USER_PW = "@aghA87plJ1,"
USER_MKT = "MILANESEKOREA"
PWD_MKT = "4RDf55<lwja*"

HEADERS = {
    "USER_MKT": USER_MKT,
    "PWD_MKT": PWD_MKT,
    "LANGUAGE": "en"
}

# 저장 경로 및 파일명 (테스트용)
SAVE_PATH = Path("export/MINETTI")
SAVE_PATH.mkdir(parents=True, exist_ok=True)
SAVE_FILE = SAVE_PATH / "MINETTI_goods_test.json"  # 파일명 변경됨

def fetch_and_save_goods():
    url = "https://www2.atelier-hub.com/hub/GoodsList"
    page = 1
    page_size = 100
    all_goods = []

    while True:
        params = {
            "Page": page,
            "PageSize": page_size,
            "retailer": "MINETTI"
        }

        res = requests.get(url, headers=HEADERS, auth=HTTPBasicAuth(USER_ID, USER_PW), params=params)

        if res.status_code != 200:
            print(f"❌ 요청 실패 (Page {page}): {res.status_code}")
            break

        data = res.json()
        goods = data.get("GoodsList", {}).get("Good", [])

        print(f"📦 Page {page} - 수집: {len(goods)}개")
        all_goods.extend(goods)

        if len(goods) < page_size:
            print("🛑 마지막 페이지 도달")
            break

        page += 1

    # 저장
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(all_goods, f, indent=2, ensure_ascii=False)

    print(f"✅ 저장 완료: {SAVE_FILE} (총 {len(all_goods)}개)")

fetch_and_save_goods()
