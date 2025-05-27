import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

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
    "SIZEPRICE": "ON",
    "DETAILEDSIZE": "ON"
}
RETAILER_NAME = "BINI"

# ✅ 1단계: GoodsList 수집
def fetch_all_goods_bini(page_size=100):
    all_goods = []
    page = 1

    while True:
        url = f"{BASE_URL}GoodsList"
        params = {
            "pageNum": page,
            "pageSize": page_size,
            "retailer": RETAILER_NAME
        }

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                auth=HTTPBasicAuth(USER_ID, USER_PW),
                timeout=10
            )
            if response.status_code != 200:
                print(f"❌ 상품 수집 실패 (status {response.status_code})")
                break

            data = response.json()
            goods = data.get("GoodsList", {}).get("Good", [])
            if not goods:
                break

            all_goods.extend(goods)
            page += 1
        except Exception as e:
            print(f"❌ 상품 수집 예외:", e)
            break

    df = pd.DataFrame(all_goods)
    print(f"✅ 상품 수집 완료: {len(df)}개")
    return df

# ✅ 2단계: 가격 + 재고 수집 (병렬)
def fetch_price_and_stock(goods_id):
    price_info = {}
    stock_info = []

    try:
        # 가격 수집
        price_res = requests.get(
            f"{BASE_URL}GoodsPriceList",
            headers=HEADERS,
            params={"GoodsID": goods_id, "retailer": RETAILER_NAME},
            auth=HTTPBasicAuth(USER_ID, USER_PW),
            timeout=10
        )
        if price_res.status_code == 200:
            for retailer in price_res.json().get("Retailers", []):
                for item in retailer.get("SizePrices", []):
                    price_info[item["Barcode"]] = {
                        "Size": item.get("Size"),
                        "SizeNetPrice": item.get("SizeNetPrice")
                    }

        # 재고 수집
        stock_res = requests.get(
            f"{BASE_URL}GoodsDetailList",
            headers=HEADERS,
            params={"GoodsID": goods_id, "retailer": RETAILER_NAME},
            auth=HTTPBasicAuth(USER_ID, USER_PW),
            timeout=10
        )
        if stock_res.status_code == 200:
            for item in stock_res.json().get("Stock", {}).get("Item", []):
                barcode = item.get("Barcode")
                stock_info.append({
                    "GoodsID": goods_id,
                    "Barcode": barcode,
                    "Size": item.get("Size"),
                    "Qty": item.get("Qty"),
                    "SizeNetPrice": price_info.get(barcode, {}).get("SizeNetPrice")
                })

    except Exception as e:
        print(f"❌ 예외 발생 (GoodsID {goods_id}): {e}")

    return stock_info

# ✅ 3단계: 병렬 수집 + 병합 + 저장
def fetch_all_bini_data_and_save(output_excel_path):
    # 1. 상품 수집
    base_df = fetch_all_goods_bini()

    # 2. 상품 ID 추출
    goods_ids = base_df["ID"].dropna().unique().tolist()
    merged_data = []

    # 3. 병렬 실행
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_price_and_stock, gid) for gid in goods_ids]
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    merged_data.extend(result)
            except Exception as e:
                print("❌ 병렬 처리 중 오류:", e)

    # 4. 병합 + 저장
    option_df = pd.DataFrame(merged_data)
    final_df = pd.merge(base_df, option_df, on="GoodsID", how="left")

    os.makedirs(os.path.dirname(output_excel_path), exist_ok=True)
    final_df.to_excel(output_excel_path, index=False)
    print(f"✅ 병렬 수집 완료: 상품 {len(base_df)}건, 옵션 {len(option_df)}건")
    print(f"📄 저장 파일: {output_excel_path}")

# ✅ 실행
if __name__ == "__main__":
    fetch_all_bini_data_and_save("export/bini_final_merged_parallel.xlsx")
