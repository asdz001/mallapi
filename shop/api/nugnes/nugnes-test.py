import requests
import json
import time
import os

# ===================== 설정 =====================
STORE_CODE = "91D5T"
BASE_URL = "https://read.efashion.cloud/api/v3.0/products/condensed"
EXPORT_DIR = "export/nugnes"
os.makedirs(EXPORT_DIR, exist_ok=True)
OUTPUT_PATH = os.path.join(EXPORT_DIR, "nugnes_full_catalog.json")

LIMIT = 500         # 한 페이지 당 최대 수량
SLEEP_SEC = 0.5     # 요청 간 딜레이
MAX_PAGES = 1000    # 안전장치: 최대 1000페이지까지 시도
# =================================================

all_items = []
offset = 0
page = 1

print("📡 전체 카탈로그 수집 시작...")

while page <= MAX_PAGES:
    params = {
        "storeCode": STORE_CODE,
        "format": "json",
        "limit": LIMIT,
        "offset": offset
    }

    try:
        res = requests.get(BASE_URL, params=params, timeout=20)
        if res.status_code != 200:
            print(f"❌ HTTP 오류 (페이지 {page}): {res.status_code}")
            break

        data = res.json()
        items = data.get("results", {}).get("items", [])

        if not items:
            print(f"⛔ 더 이상 데이터 없음 (페이지 {page})")
            break

        all_items.extend(items)
        print(f"✅ 페이지 {page} 수집 성공: {len(items)}개")

        offset += LIMIT
        page += 1
        time.sleep(SLEEP_SEC)

    except Exception as e:
        print(f"❌ 예외 발생 (페이지 {page}): {e}")
        break

# JSON 파일로 저장
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(all_items, f, ensure_ascii=False, indent=2)

print(f"\n🎉 수집 완료: 총 {len(all_items)}개 상품 → {OUTPUT_PATH}")
