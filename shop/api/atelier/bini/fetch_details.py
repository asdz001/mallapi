import requests
import json
import os
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed

# 거래처 식별자
RETAILER = "BINI"
RETAILER_UPPER = RETAILER.upper()
BASE_PATH = os.path.join("export", RETAILER)

INPUT_PATH = os.path.join(BASE_PATH, f"{RETAILER}_goods.json")
OUTPUT_PATH = os.path.join(BASE_PATH, f"{RETAILER}_details.json")
FAIL_LOG_PATH = os.path.join(BASE_PATH, f"{RETAILER}_details_failed.json")

MAX_WORKERS = 20
LIMIT = None  # 테스트 시 100 등으로 제한 가능

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

# ✅ 단일 GoodsID 요청 함수
def fetch_detail(goods_id):
    try:
        res = requests.get(
            "https://www2.atelier-hub.com/hub/GoodsDetailList",
            headers=HEADERS,
            params={"GoodsID": goods_id, "retailer": RETAILER_UPPER},
            auth=HTTPBasicAuth(USER_ID, USER_PW),
            timeout=10
        )
        if res.status_code != 200:
            return None, f"❌ 상태 코드 {res.status_code}"

        data = res.json().get("GoodsDetailList", {}).get("Good", [])
        return data[0] if data else None, None

    except Exception as e:
        return None, f"❌ 예외 발생: {e}"

# ✅ 전체 수집
def fetch_all_details():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        goods = json.load(f)

    goods_ids = [str(g["ID"]) for g in goods]
    if LIMIT:
        goods_ids = goods_ids[:LIMIT]

    print(f"📦 수집 대상 상품 수: {len(goods_ids)}개")

    results = []
    failed = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_detail, gid): gid
            for gid in goods_ids
        }

        for i, future in enumerate(as_completed(futures), 1):
            gid = futures[future]
            try:
                result, error = future.result()
                if result:
                    results.append(result)
                    print(f"[{i}] ✅ GoodsID {gid} - 상세 수집됨")
                else:
                    print(f"[{i}] ⚠️ GoodsID {gid} - 실패: {error}")
                    failed[gid] = error
            except Exception as e:
                failed[gid] = str(e)

    os.makedirs(BASE_PATH, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    with open(FAIL_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(failed, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 상세정보 수집 완료: {len(results)}개")
    print(f"❌ 실패 수: {len(failed)}개")
    print(f"📄 저장 파일: {OUTPUT_PATH}")

    with open("export/BINI/BINI_details.done", "w") as f:
        f.write("done")


if __name__ == "__main__":
    fetch_all_details()

