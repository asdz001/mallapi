import requests
import json
from requests.auth import HTTPBasicAuth

USER_ID = "Marketplace2"
USER_PW = "@aghA87plJ1,"
USER_MKT = "MILANESEKOREA"
PWD_MKT = "4RDf55<lwja*"

HEADERS = {
    "USER_MKT": USER_MKT,
    "PWD_MKT": PWD_MKT,
    "LANGUAGE": "en"
}

def check_total_goods():
    url = "https://www2.atelier-hub.com/hub/GoodsList"
    page = 1
    page_size = 100
    total_count = 0

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
        total_count += len(goods)

        if len(goods) < page_size:
            break  # 마지막 페이지 도달

        page += 1

    print(f"✅ 전체 상품 수: {total_count}")

check_total_goods()
