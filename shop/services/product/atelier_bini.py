import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
import os

# 기본 인증 계정
USER_ID = "Marketplace2"
USER_PW = "@aghA87plJ1,"

# 헤더 인증 정보
USER_MKT = "MILANESEKOREA"
PWD_MKT = "4RDf55<lwja*"

BASE_URL = "https://www2.atelier-hub.com/hub/"
RETAILER_NAME = "BINI"  # ✅ 비니실비아로 변경

def fetch_all_goods_bini(page_size=100):
    all_goods = []
    page = 1

    while True:
        url = f"{BASE_URL}GoodsList"
        params = {
            "pageNum": page,
            "pageSize": page_size,
            "retailer": RETAILER_NAME,
        }
        headers = {
            "USER_MKT": USER_MKT,
            "PWD_MKT": PWD_MKT,
            "LANGUAGE": "en",
            "DESCRIPTION": "ALL",
            "SIZEPRICE": "ON",
            "DETAILEDSIZE": "ON",
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                auth=HTTPBasicAuth(USER_ID, USER_PW),
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            print("❌ 요청 실패:", e)
            break

        if response.status_code != 200:
            print(f"❌ 요청 실패: {response.status_code}")
            break

        try:
            data = response.json()
        except Exception as e:
            print("❌ JSON 파싱 실패:", e)
            break

        goods = data.get("GoodsList", {}).get("Good", [])
        if not goods:
            break

        all_goods.extend(goods)
        page += 1

    if not all_goods:
        print("❗ 수집된 상품이 없습니다.")
        return

    os.makedirs("export", exist_ok=True)
    output_path = os.path.join("export", "atelier_bini.xlsx")
    pd.DataFrame(all_goods).to_excel(output_path, index=False)
    print(f"✅ 총 {len(all_goods)}개 상품을 수집하였습니다.")
    print(f"✅ 엑셀 저장 완료: {output_path}")

if __name__ == "__main__":
    fetch_all_goods_bini()
