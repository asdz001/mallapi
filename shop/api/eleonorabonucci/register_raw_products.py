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
BATCH_SIZE = 1000
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
            'products_updated': 0,  # ✅ 업데이트 통계 추가
            'products_skipped': 0,
            'options_created': 0,
            'options_updated': 0,   # ✅ 업데이트 통계 추가
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
    
    def normalize_value(self, value) -> str:
        """🔧 비교용 값 정규화 (None → "", 숫자 → 문자열)"""
        if value is None:
            return ""
        return str(value).strip()

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
        product_url = item.get("Url", "")  # ✅ 상품 URL 추출
        
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
                    option_url=product_url,  # ✅ 상품 URL 할당
                )
                options.append(option)
                
            except (ValueError, TypeError) as e:
                self.stats['errors'].append(f"옵션 생성 실패 {opt.get('SKU_item')}: {e}")
                logger.error(f"❌ 옵션 생성 실패: {e}")
                self.stats['options_skipped'] += 1
                continue
        
        return options
    
    def register_products(self) -> bool:
        """
        🔄 전체 상품 등록 프로세스 (업데이트 로직 포함)
        
        흐름:
        1. JSON 데이터 로드
        2. 기존 상품+옵션 전체 조회 및 매핑
        3. 각 상품별로 신규/기존 구분하여 처리
        4. 상품: 가격 비교 후 업데이트 대상 선별
        5. 옵션: 재고/가격/URL 비교 후 업데이트 대상 선별
        6. bulk_create + bulk_update로 대량 처리
        7. 솔드아웃 처리
        """
        try:
            # 1️⃣ 데이터 로드
            data = self.load_json_data()
            self.stats['total_items'] = len(data)
            
            # 2️⃣ 기존 상품과 옵션 전체 조회 (뉴네스 방식 적용)
            logger.info("🔍 기존 상품 및 옵션 조회 중...")
            existing_products = RawProduct.objects.filter(retailer=RETAILER_CODE)
            existing_product_map = {p.external_product_id: p for p in existing_products}
            
            existing_options = RawProductOption.objects.filter(product__in=existing_products)
            existing_option_map = {(o.product.external_product_id, o.external_option_id): o for o in existing_options}
            
            logger.info(f"📊 기존 상품: {len(existing_product_map)}개, 기존 옵션: {len(existing_option_map)}개")
            
            # 3️⃣ 처리 대상 리스트 초기화
            products_to_create = []
            products_to_update = []
            options_to_create = []
            options_to_update = []
            
            logger.info("🔄 상품 데이터 처리 중...")
            
            # 4️⃣ 각 상품별로 처리
            for i, item in enumerate(data, 1):
                sku = item.get("SKU")
                
                if not sku:
                    self.stats['products_skipped'] += 1
                    continue
                
                # 상품 유효성 검증 (재고 체크 포함)
                if not self.validate_product_data(item):
                    self.stats['products_skipped'] += 1
                    continue
                
                # 새 상품 데이터 준비
                supply_price, market_price = self.get_representative_price(item)
                
                existing_product = existing_product_map.get(sku)
                
                if existing_product:
                    # 🔧 기존 상품: 가격만 비교하여 업데이트 여부 결정
                    price_changed = False
                    
                    old_price_org = self.normalize_value(existing_product.price_org)
                    new_price_org = self.normalize_value(supply_price)
                    old_price_retail = self.normalize_value(existing_product.price_retail)
                    new_price_retail = self.normalize_value(market_price)
                    
                    if old_price_org != new_price_org:
                        existing_product.price_org = supply_price
                        price_changed = True
                        logger.debug(f"💰 공급가 변경: {sku} {old_price_org} → {new_price_org}")
                    
                    if old_price_retail != new_price_retail:
                        existing_product.price_retail = market_price
                        price_changed = True
                        logger.debug(f"💰 소매가 변경: {sku} {old_price_retail} → {new_price_retail}")
                    
                    if price_changed:
                        products_to_update.append(existing_product)
                        logger.info(f"🔄 상품 업데이트 대상: {sku}")
                else:
                    # 🔧 새 상품: 생성 대상
                    product_obj = self.create_product_object(item)
                    if product_obj:
                        products_to_create.append(product_obj)
                
                # 진행 상황 로그
                if i % 100 == 0:
                    logger.info(f"📦 처리 중: {i}/{len(data)} ({i/len(data)*100:.1f}%)")
            
            logger.info(f"✅ 상품 처리 완료: 생성 {len(products_to_create)}개, 업데이트 {len(products_to_update)}개")

            # 5️⃣ 수집된 SKU 목록 (솔드아웃 처리용)
            collected_ids = set(item["SKU"] for item in data if item.get("SKU") and self.validate_product_data(item))

            # 6️⃣ 복원 처리 (soldout → pending)
            restored_count = RawProduct.objects.filter(
                retailer=RETAILER_CODE,
                external_product_id__in=collected_ids,
                status="soldout"
            ).update(status="pending")
            
            if restored_count > 0:
                logger.info(f"🔄 상품 복원: {restored_count}개 (soldout → pending)")

            # 7️⃣ 이번에 수집되지 않은 상품은 soldout 처리
            soldout_count = RawProduct.objects.filter(
                retailer=RETAILER_CODE
            ).exclude(
                external_product_id__in=collected_ids
            ).update(status="soldout")
            
            if soldout_count > 0:
                logger.info(f"📦 품절 처리: {soldout_count}개 (pending → soldout)")
            
            # 8️⃣ 데이터베이스 저장 시작
            if not products_to_create and not products_to_update:
                logger.warning("⚠️ 등록/업데이트할 상품이 없습니다.")
                return False
            
            logger.info("💾 데이터베이스 저장 시작...")
            
            with transaction.atomic():
                # 🔧 상품 대량 처리
                if products_to_create:
                    inserted_products = RawProduct.objects.bulk_create(
                        products_to_create, 
                        batch_size=BATCH_SIZE
                    )
                    self.stats['products_created'] = len(inserted_products)
                    logger.info(f"✅ 상품 생성: {len(inserted_products)}개")
                
                if products_to_update:
                    RawProduct.objects.bulk_update(
                        products_to_update,
                        ['price_org', 'price_retail'],  # 🔧 가격 필드만 업데이트
                        batch_size=BATCH_SIZE
                    )
                    self.stats['products_updated'] = len(products_to_update)
                    logger.info(f"✅ 상품 업데이트: {len(products_to_update)}개")
                
                # 9️⃣ 업데이트된 상품 포함 전체 재조회 (옵션 처리용)
                all_products = RawProduct.objects.filter(
                    retailer=RETAILER_CODE, 
                    external_product_id__in=collected_ids
                )
                product_map = {p.external_product_id: p for p in all_products}
                
                # 🔟 옵션 처리
                for item in data:
                    sku = item.get("SKU")
                    if not sku or not self.validate_product_data(item):
                        continue
                        
                    product_obj = product_map.get(sku)
                    if not product_obj:
                        continue
                    
                    stock_items = item.get("Stock_Item", [])
                    product_url = item.get("Url", "")  # ✅ 상품 URL
                    
                    for opt in stock_items:
                        sku_item = opt.get("SKU_item")
                        if not sku_item or opt.get("Stock", 0) <= 0:
                            continue
                        
                        # 옵션 가격 결정
                        supply_price = opt.get("Supply_Price")
                        if supply_price is None:
                            supply_price = item.get("Supply_Price", 0)
                        
                        if supply_price is None:
                            continue
                        
                        key = (sku, sku_item)
                        existing_option = existing_option_map.get(key)
                        
                        stock = int(opt.get("Stock", 0))
                        price = float(supply_price)
                        option_url = product_url
                        
                        if existing_option:
                            # 🔧 기존 옵션: 재고/가격/URL만 비교
                            option_changed = False
                            
                            if existing_option.stock != stock:
                                existing_option.stock = stock
                                option_changed = True
                                logger.debug(f"📦 재고 변경: {sku_item} {existing_option.stock} → {stock}")
                            
                            old_price = self.normalize_value(existing_option.price)
                            new_price = self.normalize_value(price)
                            if old_price != new_price:
                                existing_option.price = price
                                option_changed = True
                                logger.debug(f"💰 옵션가격 변경: {sku_item} {old_price} → {new_price}")
                            
                            old_url = self.normalize_value(existing_option.option_url)
                            new_url = self.normalize_value(option_url)
                            if old_url != new_url:
                                existing_option.option_url = option_url
                                option_changed = True
                                logger.debug(f"🔗 URL 변경: {sku_item}")
                            
                            if option_changed:
                                options_to_update.append(existing_option)
                        else:
                            # 🔧 새 옵션: 생성 대상
                            new_option = RawProductOption(
                                product=product_obj,
                                external_option_id=sku_item,
                                option_name=opt.get("Size", ""),
                                price=price,
                                stock=stock,
                                option_url=option_url,
                            )
                            options_to_create.append(new_option)
                
                # 1️⃣1️⃣ 옵션 대량 처리
                if options_to_create:
                    RawProductOption.objects.bulk_create(
                        options_to_create, 
                        batch_size=BATCH_SIZE
                    )
                    self.stats['options_created'] = len(options_to_create)
                    logger.info(f"✅ 옵션 생성: {len(options_to_create)}개")
                
                if options_to_update:
                    RawProductOption.objects.bulk_update(
                        options_to_update,
                        ['stock', 'price', 'option_url'],  # 🔧 선별된 필드만 업데이트
                        batch_size=BATCH_SIZE
                    )
                    self.stats['options_updated'] = len(options_to_update)
                    logger.info(f"✅ 옵션 업데이트: {len(options_to_update)}개")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 상품 등록 실패: {e}")
            self.stats['errors'].append(f"전체 프로세스 실패: {e}")
            return False
    
    def print_summary(self):
        """등록 결과 요약 출력"""
        print("\n" + "="*60)
        print("📊 엘레노라 상품 등록 결과 (업데이트 포함)")
        print("="*60)
        print(f"📦 총 상품 수: {self.stats['total_items']:,}개")
        print(f"✅ 생성된 상품: {self.stats['products_created']:,}개")
        print(f"🔄 업데이트된 상품: {self.stats['products_updated']:,}개")  # ✅ 추가
        print(f"⏭️ 건너뛴 상품: {self.stats['products_skipped']:,}개")
        print(f"🔧 생성된 옵션: {self.stats['options_created']:,}개")
        print(f"🔄 업데이트된 옵션: {self.stats['options_updated']:,}개")  # ✅ 추가
        print(f"⏭️ 건너뛴 옵션: {self.stats['options_skipped']:,}개")
        
        if self.stats['errors']:
            print(f"❌ 오류 발생: {len(self.stats['errors'])}개")
            print("\n🔍 오류 상세 (최대 10개):")
            for error in self.stats['errors'][:10]:
                print(f"   • {error}")
            if len(self.stats['errors']) > 10:
                print(f"   ... 및 {len(self.stats['errors']) - 10}개 더")
        
        total_processed = self.stats['products_created'] + self.stats['products_updated']
        if total_processed > 0:
            success_rate = (total_processed / self.stats['total_items']) * 100
            print(f"📈 처리 성공률: {success_rate:.1f}%")
        
        print("="*60)

# ✅ 메인 실행 함수
def register_raw_products_from_json(test_mode: bool = True):
    """엘레노라 상품 등록 메인 함수 (업데이트 로직 포함)"""
    registrar = EleonoraRegistration(test_mode=test_mode)
    
    try:
        success = registrar.register_products()
        registrar.print_summary()

        if success:
            logger.info("🎉 상품 등록/업데이트 완료!")
        else:
            logger.error("💥 상품 등록/업데이트 실패!")

        # ✅ 생성+업데이트된 상품 수 리턴
        total_processed = registrar.stats['products_created'] + registrar.stats['products_updated']
        return total_processed

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