import pandas as pd
import requests
import os
import re
import json
import numpy as np

# ============ 설정 ============
CSV_URL = "https://feedfiles.woolytech.com/nugnes-1920.myshopify.com/yH1YCJhVtJ.csv"
EXPORT_DIR = "export/nugnes"
os.makedirs(EXPORT_DIR, exist_ok=True)

CSV_PATH = os.path.join(EXPORT_DIR, "nugnes_b2b.csv")
OUTPUT_JSON_PATH = os.path.join(EXPORT_DIR, "nugnes_processed_products.json")
# ==============================

# 1. CSV 다운로드
print("📥 CSV 다운로드 중...")
res = requests.get(CSV_URL)
with open(CSV_PATH, "wb") as f:
    f.write(res.content)
print(f"✅ 저장됨: {CSV_PATH}")

# 2. CSV 로드 및 컬럼 정리
df = pd.read_csv(CSV_PATH, encoding="ISO-8859-1")
df.columns = df.columns.str.strip()  # 컬럼명 공백 제거

# 3. 대표상품 ID 추출 (LINK IMMAGINE 1 → v=숫자)
def extract_product_id(url):
    match = re.search(r"v=(\d+)", str(url))
    return match.group(1) if match else ""

# 4. 옵션 ID 추출 (PRODUCT LINK → variant=숫자)
def extract_option_id(url):
    match = re.search(r"variant=(\d+)", str(url))
    return match.group(1) if match else ""

df["product_id"] = df["LINK IMMAGINE 1"].apply(extract_product_id)
df["option_id"] = df["PRODUCT LINK"].apply(extract_option_id)

# 5. 대표상품 기준으로 옵션 묶기 (기존 필드 유지 + 옵션 요약 + 정제)
def group_product_with_options(group):
    # 대표 필드에서 제거할 키
    exclude_keys = ["SIZE", "option_id"]

    # 대표상품 정보
    product_data = group.iloc[0].to_dict()

    # 불필요한 대표 키 제거
    for key in exclude_keys:
        product_data.pop(key, None)

    # 옵션 리스트 생성
    options = []
    total_quantity = 0

    for _, row in group.iterrows():
        option = {
            "size": row.get("SIZE") or "",
            "stock": row.get("QUANTITY") or 0,
            "price": row.get("DISCOUNTED PRICE") or "",
            "option_id": row.get("option_id") or "",
            "variant_url": row.get("PRODUCT LINK") or "",
        }
        options.append(option)
        try:
            total_quantity += int(row.get("QUANTITY") or 0)
        except:
            pass

    # 옵션 및 총재고 추가
    product_data["options"] = options
    product_data["QUANTITY"] = total_quantity
    product_data["product_id"] = group["product_id"].iloc[0]

    return product_data

# 유효한 product_id 기준으로 그룹핑
grouped_products = (
    df[df["product_id"].notna()]
    .groupby("product_id")
    .apply(group_product_with_options)
    .tolist()
)

# 6. NaN → 빈 문자열로 정리
def clean_nans(obj):
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(i) for i in obj]
    elif pd.isna(obj) or obj is np.nan:
        return ""
    return obj

cleaned_products = clean_nans(grouped_products)

# 7. JSON 파일로 저장
with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(cleaned_products, f, ensure_ascii=False, indent=2)

print(f"🎉 상품 가공 완료 → {OUTPUT_JSON_PATH}")
