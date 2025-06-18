# baseblu_single.py
import requests
import sys

BASE_URL = "https://api.csplatform.io"
TOKEN = "61a61031e8107c472fc312f3-6791f518791ad1287012b863:b151b2e915b67e6bbafd22e230f959bb"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def fetch_sku_from_api(option_id):
    try:
        url = f"{BASE_URL}/shop/v1/items/{option_id}"
        response = requests.get(url, headers=HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()
        sku = data.get("content", {}).get("sku")  # ← 여기만 바뀜

        print("✅ 조회 성공!")
        print(f"🔢 option_id: {option_id}")
        print(f"🔖 SKU: {sku}")
        print(f"📦 전체 응답: {data}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP 오류: {e}")
    except Exception as e:
        print(f"❌ 예외 발생: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❗ 사용법: python baseblu_single.py <option_id>")
    else:
        option_id = sys.argv[1]
        fetch_sku_from_api(option_id)
