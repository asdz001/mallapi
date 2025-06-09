# shop/api/baseblu/export_json.py
import requests, json, os
from datetime import datetime
from pathlib import Path

SHOP_ID = "BASE BLU"
TOKEN = "61a61031e8107c472fc312f3-6791f518791ad1287012b863:b151b2e915b67e6bbafd22e230f959bb"
API_BASE_URL = "https://api.csplatform.io"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

EXPORT_DIR = Path("export") / SHOP_ID.upper().replace(" ", "")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_JSON = EXPORT_DIR / f"{SHOP_ID.lower().replace(' ', '_')}_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

params = {
    "_pageIndex": 0,
    "_pageSize": 250,
    "withQuantities": "true"
}

response = requests.get(f"{API_BASE_URL}/shop/v1/items", headers=headers, params=params)

if response.status_code == 200:
    data = response.json().get("content", [])
    with open(EXPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 저장 완료: {EXPORT_JSON}")
else:
    print("❌ 요청 실패:", response.status_code, response.text)
