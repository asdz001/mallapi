# shop/api/atelier/atelier_api.py

import requests
from requests.auth import HTTPBasicAuth


class Atelier:
    def __init__(self, retailer_name):
        self.retailer_name = retailer_name.lower()

        self.base_url = "https://www2.atelier-hub.com/hub/"
        self.headers = {
            "USER_MKT": "MILANESEKOREA",
            "PWD_MKT": "4RDf55<lwja*"
        }
        self.auth = HTTPBasicAuth("Marketplace2", "@aghA87plJ1,")

    def get(self, endpoint):
        url = self.base_url + endpoint
        response = requests.get(url, headers=self.headers, auth=self.auth)
        if response.status_code != 200:
            print(f"❌ 요청 실패: {endpoint} - 상태코드 {response.status_code}")
            return {}
        return response.json()

    # 상품 기본정보
    def get_goods_list(self):
        result = self.get("GoodsList")
        return result.get("GoodsList", {}).get("Good", [])

    # 옵션별 재고
    def get_goods_details(self):
        result = self.get("GoodsDetailList")
        return result.get("GoodsDetailList", {}).get("Good", [])

    # 옵션별 가격
    def get_goods_prices(self):
        result = self.get("GoodsPriceList")
        return result.get("GoodsPriceList", {}).get("Price", [])

    # 브랜드 목록
    def get_brand_list(self):
        result = self.get("BrandList")
        return result.get("BrandList", {}).get("Brand", [])

    # 성별 목록
    def get_gender_list(self):
        result = self.get("GenderList")
        return result.get("GenderList", {}).get("Gender", [])

    # 서브카테고리 (대분류~소분류)
    def get_subcategory_list(self):
        result = self.get("SubCategoryList")
        return result.get("SubCategoryList", {}).get("SubCategory", [])
