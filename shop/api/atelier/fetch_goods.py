import requests
from .config import RETAILERS

API_BASE_URL = "https://www2.atelier-hub.com/test-MPHUB/"

# ✅ 자동 필터링 함수 (거래처 중 enabled=True 인 것만 뽑기)
def get_active_retailers():
    return [r_id for r_id, info in RETAILERS.items() if info.get("enabled")]

# ✅ 메인 함수: 거래처 상품리스트 가져오기
def get_goods_list(retailer_id, page_num=1, page_size=50):
    if retailer_id not in RETAILERS:
        raise ValueError(f"등록되지 않은 Retailer ID: {retailer_id}")

    credentials = RETAILERS[retailer_id]

    headers = {
        "USER_MKT": credentials["USER_MKT"],
        "PWD_MKT": credentials["PWD_MKT"],
        "LANGUAGE": "en",
        "DESCRIPTION": "ALL"
    }

    url = f"{API_BASE_URL}GoodsList?pageNum={page_num}&pageSize={page_size}&retailer={retailer_id}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"[Atelier Error] Retailer {retailer_id} - {response.status_code} : {response.text}")
        return None
