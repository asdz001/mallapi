import requests
import json
import os
from requests.auth import HTTPBasicAuth

# 거래처 식별자
RETAILER = "CUCCUINI"
BASE_PATH = os.path.join("export", RETAILER)
os.makedirs(BASE_PATH, exist_ok=True)

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

# ✅ 공통 저장 함수
def save_json_from_api(url, key, filename):
    res = requests.get(url, headers=HEADERS, auth=HTTPBasicAuth(USER_ID, USER_PW))
    if res.status_code != 200:
        print(f"❌ 요청 실패 ({url}): 상태 코드 {res.status_code}")
        return

    top_level = res.json().get(key, {})
    second_key = list(top_level.keys())[0] if isinstance(top_level, dict) and top_level else None
    data = top_level.get(second_key, []) if second_key else []

    filepath = os.path.join(BASE_PATH, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 저장 완료: {filepath} ({len(data)}개)")

def fetch_brand_and_category_CUCCUINI():
    print("📦 브랜드 및 카테고리 수집 시작")
    save_json_from_api("https://www2.atelier-hub.com/hub/CategoryList", "CategoryList", f"{RETAILER}_category_mapping.json")
    save_json_from_api("https://www2.atelier-hub.com/hub/BrandList", "BrandList", f"{RETAILER}_brand_mapping.json")
    save_json_from_api("https://www2.atelier-hub.com/hub/GenderList", "GenderList", f"{RETAILER}_gender_mapping.json")