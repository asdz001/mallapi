# shop/api/nugnes.py

import pandas as pd
import requests
from shop.models import RawProduct, RawProductOption
from django.utils.timezone import now
from common.utils import download_image_from_url
import logging

logger = logging.getLogger(__name__)

CSV_FEED_URL = "https://feedfiles.woolytech.com/nugnes-1920.myshopify.com/yH1YCJhVtJ.csv "
RETAILER_CODE = "IT-N-01"  # 뉴네스 거래처 코드

def fetch_nugnes_products():
    """
    뉴네스 상품 수집 함수
    - CSV 피드에서 상품 정보를 수집하여 RawProduct, RawProductOption 저장
    """
    logger.info("📥 뉴네스 상품 수집 시작")
    df = pd.read_csv(CSV_FEED_URL)

    total = 0
    for _, row in df.iterrows():
        try:
            product_code = row["Product Code"]
            color = row["Color"]
            size = row["Size"]
            barcode = row["EAN"]
            name = row["Product Description"]
            brand = row["Brand"]
            price = float(row["Price"])  # 세금 포함
            stock = int(row["Stock"])
            image_url = row.get("Image1", "")

            # ✅ RawProduct 저장 또는 업데이트
            raw, _ = RawProduct.objects.update_or_create(
                retailer=RETAILER_CODE,
                product_code=product_code,
                color_code=color,
                defaults={
                    "product_name": name,
                    "brand_name": brand,
                    "currency": "EUR",
                    "origin_price": price,
                    "image_url": image_url,
                    "fetched_at": now(),
                }
            )

            # ✅ RawProductOption 저장
            RawProductOption.objects.update_or_create(
                raw_product=raw,
                size=size,
                defaults={
                    "stock": stock,
                    "price": price,
                    "barcode": barcode,
                }
            )
            total += 1

        except Exception as e:
            logger.warning(f"❌ 상품 처리 실패: {e}")
            continue

    logger.info(f"✅ 수집 완료: 총 {total}개 상품")

    return total

def main():
    return fetch_nugnes_products()
