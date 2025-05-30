import requests
from requests.auth import HTTPBasicAuth


class Atelier:
    def __init__(self, retailer: str):
        self.retailer = retailer  # 원본 그대로 사용

        # 아뜰리에 API 기본 URL (운영 서버 기준)
        self.base_url = "https://www2.atelier-hub.com/hub/"

        # 사용자 인증 정보 (테스트/운영 서버에 따라 교체 가능)
        self.user_id = "Marketplace2"
        self.user_pw = "@aghA87plJ1,"
        self.user_mkt = "MILANESEKOREA"
        self.pwd_mkt = "4RDf55<lwja*"

        # API 호출 시 공통적으로 필요한 헤더
        self.headers = {
            "USER_MKT": self.user_mkt,
            "PWD_MKT": self.pwd_mkt,
            "LANGUAGE": "en",
            "DESCRIPTION": "ALL",
            "SIZEPRICE": "ON",
            "DETAILEDSIZE": "ON"
        }

        # BASIC 인증 처리
        self.auth = HTTPBasicAuth(self.user_id, self.user_pw)

    def _get(self, endpoint: str, params: dict = None):
        """
        내부 공통 GET 요청 함수
        :param endpoint: API 엔드포인트 이름
        :param params: GET 파라미터 딕셔너리
        """
        try:
            response = requests.get(
                self.base_url + endpoint,
                headers=self.headers,
                auth=self.auth,
                params=params or {}  # 파라미터 없을 경우 빈 딕셔너리 사용
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ {endpoint} 호출 실패: {e}")
            return {}

    # 상품 목록 조회 (Good 객체 리스트 포함)
    def get_goods_list(self):
        return self._get("GoodsList", {"retailer": self.retailer})

    # 상품 상세 정보 (옵션, 재고, 이미지 등 포함)
    def get_goods_detail_list(self):
        return self._get("GoodsDetailList", {"retailer": self.retailer})

    # 상품별 가격 정보 (리테일러별 가격 포함)
    def get_goods_price_list(self):
        return self._get("GoodsPriceList", {"retailer": self.retailer})

    # 브랜드 목록 (ID → 이름 매핑용)
    def get_brand_list(self):
        return self._get("BrandList")

    # 성별 정보 (예: Men, Women)
    def get_gender_list(self):
        return self._get("GenderList")

    # 대분류 카테고리 정보
    def get_category_list(self):
        return self._get("CategoryList")

    # 중/소분류 카테고리 정보
    def get_subcategory_list(self):
        return self._get("SubCategoryList")

    # 시즌 정보 (FW24, SS25 등)
    def get_season_list(self):
        return self._get("SeasonList")

    # 색상 정보
    def get_color_list(self):
        return self._get("ColorList")

    # 옵션별 재고 정보 (사용하지 않을 예정이나 호출 가능)
    def get_stock_list(self):
        return self._get("GoodsStockList", {"retailer": self.retailer})

    # 주문 상태 확인용
    def get_order_status_list(self):
        return self._get("OrderStatusList")

    # 거래처(리테일러) 목록 확인용
    def get_retailers_list(self):
        return self._get("RetailersList")