import json
import logging
from pathlib import Path
from shop.models import RawProduct, RawProductOption 
from django.db import transaction, IntegrityError
from typing import Dict, List, Tuple, Optional

# ✅ 설정 상수
RETAILER_CODE = "IT-E-01"
RETAILER_NAME = "ELEONORA"
JSON_PATH = Path("export") / RETAILER_NAME / "eleonora_merged_raw_products.json"
BATCH_SIZE = 500
TEST_LIMIT = None  # 테스트용 제한 (나중에 None으로 변경)

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EleonoraRegistration:
    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self.stats = {
            'total_items': 0,
            'products_created': 0,
            'products_skipped': 0,
            'products_updated': 0,
            'options_created': 0,
            'options_skipped': 0,
            'errors': []
        }
    
    def load_json_data(self) -> List[Dict]:
        """JSON 파일 로드 및 검증"""
        try:
            if not JSON_PATH.exists():
                raise FileNotFoundError(f"JSON 파일이 없습니다: {JSON_PATH}")
            
            logger.info(f"📁 JSON 파일 로드 중: {JSON_PATH}")
            
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                raise ValueError("JSON 데이터가 리스트 형태가 아닙니다")
            
            logger.info(f"✅ JSON 로드 완료: {len(data)}개 항목")
            
            # 🔧 테스트 모드 처리
            if self.test_mode and TEST_LIMIT:
                data = data[:TEST_LIMIT]
                logger.info(f"🧪 테스트 모드: {len(data)}개 항목으로 제한")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ JSON 로드 실패: {e}")
            raise
    
    def build_product_name(self, item: Dict) -> str:
        """상품명 구성"""
        name = item.get("Product_Name", "").strip()
        brand = item.get("Product_Brand", "").strip()
        product_id = item.get("ProductID", "").strip()
        
        # 브랜드가 이름에 포함되어 있지 않으면 추가
        if brand and brand.upper() not in name.upper():
            name = f"{brand} {name}"
        
        # ProductID 추가 (중복되지 않게)
        if product_id and product_id not in name:
            name = f"{name} {product_id}"
        
        return name.strip()
    
    def build_description(self, item: Dict) -> str:
        """상품 설명 구성"""
        desc_parts = []
        
        # 기본 설명
        if item.get("Description"):
            desc_parts.append(item["Description"].strip())
        
        # 사이즈 정보
        if item.get("SizeInfo"):
            desc_parts.append(f"사이즈: {item['SizeInfo']}")
        
        # 소재 정보
        if item.get("Product_Material"):
            desc_parts.append(f"소재: {item['Product_Material']}")
        
        # 제조국
        if item.get("Product_MADEin"):
            desc_parts.append(f"제조국: {item['Product_MADEin']}")
        
        # 상품 상세
        if item.get("Product_Detail"):
            desc_parts.append(f"상세: {item['Product_Detail']}")
        
        return "\n".join(desc_parts)
    
    def get_representative_price(self, item: Dict) -> Tuple[float, float]:
        """상품의 대표 가격 추출 (상품 레벨 가격 우선 사용)"""
        # 상품 레벨 가격 직접 사용 (API에서 이미 대표가격 제공)
        supply_price = item.get("Supply_Price")
        market_price = item.get("Market_Price")
        
        # 상품 레벨 가격이 있으면 직접 사용
        if supply_price is not None and market_price is not None:
            return float(supply_price), float(market_price)
        
        # Fallback: 상품 레벨 가격이 없을 때만 옵션에서 최고가 계산
        logger.warning(f"상품 레벨 가격 없음, 옵션에서 계산: SKU={item.get('SKU')}")
        
        stock_items = item.get("Stock_Item", [])
        if not stock_items:
            return 0.0, 0.0
        
        # 재고가 있는 옵션들 우선
        available_options = [
            opt for opt in stock_items 
            if opt.get("Stock", 0) > 0 and 
               opt.get("Supply_Price") is not None and 
               opt.get("Market_Price") is not None
        ]
        
        # 재고가 없어도 가격 정보가 있는 옵션들
        if not available_options:
            all_options = [
                opt for opt in stock_items 
                if opt.get("Supply_Price") is not None and 
                   opt.get("Market_Price") is not None
            ]
            available_options = all_options
        
        if not available_options:
            return 0.0, 0.0
        
        # 최고가 계산
        max_supply = max(float(opt.get("Supply_Price", 0)) for opt in available_options)
        max_market = max(float(opt.get("Market_Price", 0)) for opt in available_options)
        
        return max_supply, max_market
    
    def extract_images(self, item: Dict) -> Dict[str, Optional[str]]:
        """이미지 URL 추출 (최대 4장)"""
        pictures = item.get("Picture", [])
        image_data = {}
        
        for i in range(4):
            if i < len(pictures) and pictures[i]:
                image_data[f"image_url_{i+1}"] = pictures[i]
            else:
                image_data[f"image_url_{i+1}"] = None
        
        return image_data
    
    def has_available_stock(self, item: Dict) -> bool:
        """상품에 재고가 있는 옵션이 하나라도 있는지 확인"""
        stock_items = item.get("Stock_Item", [])
        
        for opt in stock_items:
            if opt.get("Stock", 0) > 0:
                return True
        
        return False
    
    def validate_product_data(self, item: Dict) -> bool:
        """상품 데이터 유효성 검증"""
        sku = item.get("SKU")
        product_id = item.get("ProductID")
        product_name = item.get("Product_Name")
        
        if not sku:
            self.stats['errors'].append(f"SKU 없음: {item}")
            return False
        
        if not product_id:
            self.stats['errors'].append(f"ProductID 없음: SKU={sku}")
            return False
        
        if not product_name:
            self.stats['errors'].append(f"Product_Name 없음: SKU={sku}")
            return False
        
        # 🔧 추가: 재고가 있는 옵션이 하나도 없으면 상품 등록 안함
        if not self.has_available_stock(item):
            logger.info(f"⏭️ 재고 없는 상품 건너뛰기: SKU={sku}")
            return False
        
        return True
    
    def create_product_object(self, item: Dict) -> Optional[RawProduct]:
        """RawProduct 객체 생성"""
        try:
            if not self.validate_product_data(item):
                return None
            
            sku = item.get("SKU")
            supply_price, market_price = self.get_representative_price(item)
            image_data = self.extract_images(item)
            
            product = RawProduct(
                retailer=RETAILER_CODE,
                external_product_id=sku,
                sku=item.get("ProductID"),
                product_name=self.build_product_name(item),
                raw_brand_name=item.get("Product_Brand", ""),
                origin=item.get("Product_MADEin", ""),
                color=item.get("Color", ""),
                material=item.get("Product_Material", ""),
                description=self.build_description(item),
                price_org=supply_price,
                price_retail=market_price,
                gender=item.get("Gender", ""),
                category1=item.get("CategoryMaster", ""),
                category2=str(item.get("Category", "")),
                season=item.get("Season_Code", ""),
                **image_data,
            )
            
            return product
            
        except Exception as e:
            self.stats['errors'].append(f"상품 객체 생성 실패 SKU={item.get('SKU')}: {e}")
            logger.error(f"❌ 상품 객체 생성 실패: {e}")
            return None
    
    def create_option_objects(self, item: Dict, product_obj: RawProduct) -> List[RawProductOption]:
        """RawProductOption 객체들 생성"""
        options = []
        stock_items = item.get("Stock_Item", [])
        
        for opt in stock_items:
            try:
                sku_item = opt.get("SKU_item")
                if not sku_item:
                    self.stats['options_skipped'] += 1
                    continue
                
                # 🔧 재고가 0인 옵션은 제외
                if opt.get("Stock", 0) <= 0:
                    self.stats['options_skipped'] += 1
                    continue
                
                # 🔧 옵션에는 가격 필드가 하나만 있음 (공급가 사용)
                supply_price = opt.get("Supply_Price")
                
                # 옵션 레벨 가격이 없으면 상품 레벨 가격 사용
                if supply_price is None:
                    supply_price = item.get("Supply_Price", 0)
                
                if supply_price is None:
                    logger.warning(f"⚠️ 가격 정보 없음: {sku_item}")
                    self.stats['options_skipped'] += 1
                    continue
                
                option = RawProductOption(
                    product=product_obj,
                    external_option_id=sku_item,
                    option_name=opt.get("Size", ""),
                    price=float(supply_price),  # 공급가만 사용
                    stock=int(opt.get("Stock", 0)),
                )
                options.append(option)
                
            except (ValueError, TypeError) as e:
                self.stats['errors'].append(f"옵션 생성 실패 {opt.get('SKU_item')}: {e}")
                logger.error(f"❌ 옵션 생성 실패: {e}")
                self.stats['options_skipped'] += 1
                continue
        
        return options
    
    def register_products(self) -> bool:
        """전체 상품 등록 프로세스"""
        try:
            # 1. 데이터 로드
            data = self.load_json_data()
            self.stats['total_items'] = len(data)
            
            # 2. 기존 SKU 조회 (중복 방지)
            logger.info("🔍 기존 상품 SKU 조회 중...")
            existing_skus = set(
                RawProduct.objects.filter(retailer=RETAILER_CODE)
                .values_list("external_product_id", flat=True)
            )
            logger.info(f"📊 기존 상품: {len(existing_skus)}개")
            
            # 3. 상품 및 옵션 객체 생성
            new_products = []
            all_options = []
            
            logger.info("🔄 상품 데이터 처리 중...")
            
            for i, item in enumerate(data, 1):
                sku = item.get("SKU")
                
                if not sku:
                    self.stats['products_skipped'] += 1
                    continue
                
                if sku in existing_skus:
                    logger.debug(f"⏭️ 이미 존재하는 상품: {sku}")
                    self.stats['products_skipped'] += 1
                    continue
                
                # 상품 객체 생성 (재고 체크 포함)
                product_obj = self.create_product_object(item)
                if not product_obj:
                    self.stats['products_skipped'] += 1
                    continue
                
                new_products.append(product_obj)
                
                # 진행 상황 로그
                if i % 100 == 0:
                    logger.info(f"📦 처리 중: {i}/{len(data)} ({i/len(data)*100:.1f}%)")
            
            logger.info(f"✅ 처리 완료: {len(new_products)}개 상품 준비")
            
            # 4. 데이터베이스 저장
            if not new_products:
                logger.warning("⚠️ 등록할 상품이 없습니다.")
                return False
            
            logger.info("💾 데이터베이스 저장 시작...")
            
            with transaction.atomic():
                # 상품 bulk create
                inserted_products = RawProduct.objects.bulk_create(
                    new_products, 
                    batch_size=BATCH_SIZE
                )
                self.stats['products_created'] = len(inserted_products)
                logger.info(f"✅ 상품 등록: {len(inserted_products)}개")
                
                # 등록된 상품 맵핑 (옵션 등록을 위해)
                inserted_map = {p.external_product_id: p for p in inserted_products}
                
                # 옵션 생성
                for item in data:
                    sku = item.get("SKU")
                    product_obj = inserted_map.get(sku)
                    
                    if not product_obj:
                        continue
                    
                    options = self.create_option_objects(item, product_obj)
                    all_options.extend(options)
                
                # 옵션 bulk create
                if all_options:
                    RawProductOption.objects.bulk_create(
                        all_options, 
                        batch_size=BATCH_SIZE
                    )
                    self.stats['options_created'] = len(all_options)
                    logger.info(f"✅ 옵션 등록: {len(all_options)}개")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ 상품 등록 실패: {e}")
            self.stats['errors'].append(f"전체 프로세스 실패: {e}")
            return False
    
    def print_summary(self):
        """등록 결과 요약 출력"""
        print("\n" + "="*60)
        print("📊 엘레노라 상품 등록 결과")
        print("="*60)
        print(f"📦 총 상품 수: {self.stats['total_items']:,}개")
        print(f"✅ 등록된 상품: {self.stats['products_created']:,}개")
        print(f"⏭️ 건너뛴 상품: {self.stats['products_skipped']:,}개")
        print(f"🔧 등록된 옵션: {self.stats['options_created']:,}개")
        print(f"⏭️ 건너뛴 옵션: {self.stats['options_skipped']:,}개")
        
        if self.stats['errors']:
            print(f"❌ 오류 발생: {len(self.stats['errors'])}개")
            print("\n🔍 오류 상세 (최대 10개):")
            for error in self.stats['errors'][:10]:
                print(f"   • {error}")
            if len(self.stats['errors']) > 10:
                print(f"   ... 및 {len(self.stats['errors']) - 10}개 더")
        
        if self.stats['products_created'] > 0:
            success_rate = (self.stats['products_created'] / self.stats['total_items']) * 100
            print(f"📈 등록 성공률: {success_rate:.1f}%")
        
        print("="*60)

# ✅ 메인 실행 함수
def register_raw_products_from_json(test_mode: bool = True):
    """엘레노라 상품 등록 메인 함수"""
    registrar = EleonoraRegistration(test_mode=test_mode)
    
    try:
        success = registrar.register_products()
        registrar.print_summary()

        if success:
            logger.info("🎉 상품 등록 완료!")
        else:
            logger.error("💥 상품 등록 실패!")

        # ✅ 등록된 상품 수 리턴
        return registrar.stats['products_created']

    except Exception as e:
        logger.error(f"❌ 등록 프로세스 실패: {e}")
        registrar.print_summary()
        return 0
    
# ✅ 실행
if __name__ == "__main__":
    # 테스트 모드로 실행 (TEST_LIMIT = 10)
    #register_raw_products_from_json(test_mode=True)
    
    # 전체 등록 시 사용
     register_raw_products_from_json(test_mode=False)