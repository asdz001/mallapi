from django.db import transaction
from shop.models import RawProduct, RawProductOption
import requests, zipfile, io, json
from decimal import Decimal

LATTIZIP_URL = "https://lab.modacheva.com/json/json/milanese/stock.zip"


def fetch_latti_raw_products_optimized(limit=None):
    print("📥 운영용 ZIP 다운로드 중...")
    response = requests.get(LATTIZIP_URL)
    print(f"🔍 응답 상태 코드: {response.status_code}")
    print(f"🔍 응답 헤더: {response.headers}")
    if response.status_code != 200:
        print("❌ 실패")
        return

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        filename = zf.namelist()[0]
        with zf.open(filename) as raw_file:
            content = raw_file.read().decode("latin-1")
            data = json.loads(content)

    items = data.get("Dettagli", [])[:limit]
    cod_list = [item.get("COD") for item in items if item.get("COD")]
    existing = set(RawProduct.objects.filter(external_product_id__in=cod_list).values_list("external_product_id", flat=True))

    new_products = []
    new_options = []

    with transaction.atomic():
        for item in items:
            cod = item.get("COD")
            if not cod:
                continue

            model = item.get("MODEL", "").strip()
            tex = item.get("COD_TEXSTYLE", "").strip()
            color_code = item.get("COD_COLOR", "").strip()
            color_name = item.get("DESC_COLOR", "") or None
            product_name = f"{model} {tex} {color_code}".strip()
            sku = f"{model}-{tex}-{color_code}".strip()

            try:
                price = Decimal(item.get("SELLOUT", "0"))
                discount = Decimal(item.get("DISCOUNT", "0"))
                price_org = price * (Decimal("1") - discount / 100)
            except:
                price_org = Decimal("0")

            raw = RawProduct.objects.update_or_create(
                external_product_id=cod,
                defaults={
                    "retailer": "IT-R-01",
                    "raw_brand_name": item.get("BRAND"),
                    "product_name": product_name,
                    "sku": sku,
                    "gender": item.get("GENDER"),
                    "season": item.get("SEASON"),
                    "category1": item.get("FAMILY"),
                    "category2": item.get("CAT"),
                    "origin": item.get("MADEIN"),
                    "material": item.get("DESC_TEXSTYLE"),
                    "color": color_name,
                    "image_url_1": item.get("PIC1"),
                    "image_url_2": item.get("PIC2"),
                    "price_org": round(price_org, 2),
                    "price_retail": price,
                    "status": "pending"
                }
            )[0]

            raw.options.all().delete()
            barcodes = item.get("BARCODE", [])
            sizes = item.get("TGL", [])
            stocks = item.get("STOCK", [])

            for i in range(min(len(barcodes), len(sizes), len(stocks))):
                new_options.append(RawProductOption(
                    product=raw,
                    external_option_id=barcodes[i],
                    option_name=sizes[i],
                    stock=int(stocks[i])
                ))

        RawProductOption.objects.bulk_create(new_options)

    print(f"✅ 최적화 저장 완료: 상품 {len(items)}건")
