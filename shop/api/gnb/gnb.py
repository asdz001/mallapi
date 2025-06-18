import os
import sys
import logging
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict
import re

# ✅ Django 환경 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mallapi.settings")

import django
django.setup()

import csv
import io
from ftplib import FTP
from django.db import transaction
from shop.models import RawProduct, RawProductOption

# ✅ 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gnb_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ✅ 설정
FTP_HOST = "93.46.41.5"
FTP_USER = "milanese"
FTP_PSW = "X90P6jYT3Gl!"
RETAILER_CODE = "IT-G-01"
EXPORT_DIR = Path("export") / "GNB"
PROCESSED_FILE_LIST = EXPORT_DIR / "processed_files.txt"
MAIN_FILES_PROCESSED = EXPORT_DIR / "main_files_processed.txt"  # 처리된 전체파일 목록
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
BATCH_SIZE = 1000

# ✅ 파일명 패턴
MAIN_FILE_PATTERN = re.compile(r'COMPANY_\d+_\d+_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_0000001\.csv')
PARTIAL_FILE_PATTERN = re.compile(r'COMPANY_\d+_\d+_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_(\d{7})\.csv')

# ✅ 필드 매핑
COLUMNS = {
    "product_id": "IGUArticolo",
    "brand": "DSLinea",
    "name": "DSArticoloAgg",
    "model": "Modello",
    "gender": "DSSessoWeb",
    "category1": "DSRepartoWeb",
    "category2": "DSCategoriaMerceologicaWeb",
    "color": "Classificazione7",
    "description": "ArticoloDescrizionePers",
    "size": "Taglia",
    "stock": "Disponibilita",
    "price_org": "Costo",
    "price_retail": "PrezzoIvato",
    "season": "DSStagione",
    "origin": "DSMarca",
    "external_option_id": "IDArtCod",
    "material": "DSMateriale",
    "image_urls": ["URLImg1", "URLImg2", "URLImg3", "URLImg4"]
}

# ✅ 통계 클래스
class ProcessingStats:
    def __init__(self):
        self.processed_files = 0
        self.main_files_processed = 0
        self.partial_files_processed = 0
        self.total_products = 0
        self.total_options = 0
        self.filtered_zero_stock = 0
        self.new_products = 0
        self.updated_products = 0
        self.deleted_products = 0
        self.errors = []
        self.start_time = datetime.now()
    
    def add_error(self, error_msg):
        self.errors.append(error_msg)
        logger.error(error_msg)
    
    def get_summary(self):
        duration = datetime.now() - self.start_time
        return {
            'processed_files': self.processed_files,
            'main_files_processed': self.main_files_processed,
            'partial_files_processed': self.partial_files_processed,
            'total_products': self.total_products,
            'total_options': self.total_options,
            'filtered_zero_stock': self.filtered_zero_stock,
            'new_products': self.new_products,
            'updated_products': self.updated_products,
            'deleted_products': self.deleted_products,
            'duration': str(duration),
            'error_count': len(self.errors)
        }

# ✅ 파일 정보 클래스
class FileInfo:
    def __init__(self, filename):
        self.filename = filename
        self.is_main = filename.endswith("_0000001.csv")
        self.date = self.extract_date()
        self.time = self.extract_time()
        self.sequence = self.extract_sequence()
        self.sort_key = f"{self.date}_{self.time}_{self.sequence:07d}"
    
    def extract_date(self):
        """파일명에서 날짜 추출"""
        pattern = MAIN_FILE_PATTERN if self.is_main else PARTIAL_FILE_PATTERN
        match = pattern.search(self.filename)
        if match:
            return datetime.strptime(match.group(1), '%Y-%m-%d').date()
        return None
    
    def extract_time(self):
        """파일명에서 시간 추출"""
        pattern = MAIN_FILE_PATTERN if self.is_main else PARTIAL_FILE_PATTERN
        match = pattern.search(self.filename)
        if match:
            return match.group(2)  # HH-MM-SS 형태
        return "00-00-00"
    
    def extract_sequence(self):
        """파일명에서 시퀀스 번호 추출"""
        if self.is_main:
            return 1  # 전체파일은 항상 1
        else:
            match = PARTIAL_FILE_PATTERN.search(self.filename)
            if match:
                return int(match.group(3))
        return 0

# ✅ 안전한 변환 함수들
def safe_float_convert(value, default=0.0):
    try:
        if not value or value.strip() == '':
            return default
        return float(value.replace(',', ''))
    except (ValueError, TypeError, AttributeError):
        logger.warning(f"Float 변환 실패: {value}")
        return default

def safe_int_convert(value, default=0):
    try:
        if not value or value.strip() == '':
            return default
        return int(float(str(value).replace(',', '')))
    except (ValueError, TypeError, AttributeError):
        logger.warning(f"Int 변환 실패: {value}")
        return default

def safe_string_convert(value, default=""):
    try:
        return str(value).strip() if value else default
    except:
        return default

# ✅ 파일 관리 함수들
def get_processed_files():
    """처리된 파일 목록 조회"""
    try:
        return set(PROCESSED_FILE_LIST.read_text().splitlines()) if PROCESSED_FILE_LIST.exists() else set()
    except Exception as e:
        logger.error(f"처리된 파일 목록 조회 실패: {e}")
        return set()

def get_processed_main_files():
    """처리된 전체파일 목록 조회 (날짜별)"""
    try:
        processed_mains = {}
        if MAIN_FILES_PROCESSED.exists():
            for line in MAIN_FILES_PROCESSED.read_text().splitlines():
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        date_str = parts[0]
                        filename = parts[1]
                        file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        processed_mains[file_date] = filename
        return processed_mains
    except Exception as e:
        logger.error(f"처리된 전체파일 목록 조회 실패: {e}")
        return {}

def mark_processed(filename):
    """파일을 처리 완료 목록에 추가"""
    try:
        with PROCESSED_FILE_LIST.open("a", encoding='utf-8') as f:
            f.write(f"{filename}\n")
    except Exception as e:
        logger.error(f"파일 처리 완료 표시 실패: {e}")

def mark_main_processed(filename, file_date):
    """전체파일 처리 완료 표시"""
    try:
        with MAIN_FILES_PROCESSED.open("a", encoding='utf-8') as f:
            f.write(f"{file_date.strftime('%Y-%m-%d')}\t{filename}\t{datetime.now().isoformat()}\n")
    except Exception as e:
        logger.error(f"전체파일 처리 완료 표시 실패: {e}")

def get_last_processed_file_for_date(target_date, all_files):
    """특정 날짜의 마지막 처리된 파일 찾기"""
    processed_files = get_processed_files()
    
    # 해당 날짜의 파일들 중 처리된 것들만 필터링
    date_files = [f for f in all_files if f.date == target_date and f.filename in processed_files]
    
    if not date_files:
        return None
    
    # 시간순, 시퀀스순 정렬해서 마지막 파일 반환
    date_files.sort(key=lambda x: x.sort_key)
    return date_files[-1]

# ✅ 데이터 검증
def validate_product_data(product_data):
    """상품 데이터 유효성 검사"""
    if not product_data.get('external_product_id'):
        return False, "상품 ID 누락"
    
    if not product_data.get('product_name', '').strip():
        return False, "상품명 누락"
    
    if product_data.get('price_retail', 0) < 0:
        return False, "판매가격 오류"
    
    return True, None

# ✅ CSV 파서
def parse_csv(data, stats):
    """CSV 데이터 파싱"""
    try:
        content = data.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        
        products_dict = defaultdict(lambda: {
            'product_info': None,
            'options': []
        })
        
        filtered_count = 0
        
        for row_num, row in enumerate(reader, start=2):
            try:
                if not row.get(COLUMNS["product_id"]):
                    continue
                
                # 재고 확인 - 0이면 건너뛰기
                stock = safe_int_convert(row.get(COLUMNS["stock"], 0))
                if stock <= 0:
                    filtered_count += 1
                    continue
                
                product_id = safe_string_convert(row[COLUMNS["product_id"]])
                
                # 상품 기본 정보
                if products_dict[product_id]['product_info'] is None:
                    products_dict[product_id]['product_info'] = {
                        "external_product_id": product_id,
                        "product_name": f"{safe_string_convert(row.get(COLUMNS['brand'], ''))} {safe_string_convert(row.get(COLUMNS['name'], ''))} {safe_string_convert(row.get(COLUMNS['model'], ''))}".strip(),
                        "raw_brand_name": safe_string_convert(row.get(COLUMNS["brand"], "")),
                        "gender": safe_string_convert(row.get(COLUMNS["gender"], "")),
                        "category1": safe_string_convert(row.get(COLUMNS["category1"], "")),
                        "category2": safe_string_convert(row.get(COLUMNS["category2"], "")),
                        "color": safe_string_convert(row.get(COLUMNS["color"], "")),
                        "description": safe_string_convert(row.get(COLUMNS["description"], "")),
                        "price_org": safe_float_convert(row.get(COLUMNS["price_org"], 0)),
                        "price_retail": safe_float_convert(row.get(COLUMNS["price_retail"], 0)),
                        "sku": safe_string_convert(row.get(COLUMNS["model"], "")),
                        "season": safe_string_convert(row.get(COLUMNS["season"], "")),
                        "material": safe_string_convert(row.get(COLUMNS["material"], "")),
                        "origin": safe_string_convert(row.get(COLUMNS["origin"], "")),
                        "image_url_1": safe_string_convert(row.get(COLUMNS["image_urls"][0], "")),
                        "image_url_2": safe_string_convert(row.get(COLUMNS["image_urls"][1], "")),
                        "image_url_3": safe_string_convert(row.get(COLUMNS["image_urls"][2], "")),
                        "image_url_4": safe_string_convert(row.get(COLUMNS["image_urls"][3], "")),
                    }
                
                # 옵션 정보 추가
                option = {
                    "option_name": safe_string_convert(row.get(COLUMNS["size"], "ONE")),
                    "stock": stock,
                    "price": safe_float_convert(row.get(COLUMNS["price_org"], 0)),
                    "external_option_id": safe_string_convert(row.get(COLUMNS["external_option_id"], "")),
                }
                products_dict[product_id]['options'].append(option)
                
            except Exception as e:
                stats.add_error(f"행 {row_num} 파싱 오류: {e}")
                continue
        
        # 최종 상품 리스트 생성
        final_products = []
        for product_id, data in products_dict.items():
            if data['product_info'] and data['options']:
                is_valid, error_msg = validate_product_data(data['product_info'])
                if not is_valid:
                    stats.add_error(f"상품 {product_id}: {error_msg}")
                    continue
                
                product_with_options = data['product_info'].copy()
                product_with_options['options'] = data['options']
                final_products.append(product_with_options)
        
        stats.filtered_zero_stock = filtered_count
        stats.total_options = sum(len(p['options']) for p in final_products)
        
        logger.info(f"CSV 파싱 완료: 상품 {len(final_products)}개, 옵션 {stats.total_options}개 (재고0 필터링: {filtered_count}개)")
        return final_products
        
    except Exception as e:
        stats.add_error(f"CSV 파싱 실패: {e}")
        return []

# ✅ DB 등록 함수들
def register_full_sync(products, stats):
    """전체 동기화 (전체파일 기준)"""
    try:
        logger.info("전체 동기화 시작 - 전체파일 기준으로 완전 동기화")
        
        # 1. 기존 데이터 조회
        existing_products = RawProduct.objects.filter(retailer=RETAILER_CODE)
        existing_map = {p.external_product_id: p for p in existing_products}
        existing_ids = set(existing_map.keys())
        
        # 2. 들어오는 상품 ID 세트
        incoming_ids = set(p["external_product_id"] for p in products)

        RawProduct.objects.filter(
            external_product_id__in=incoming_ids,
            retailer=RETAILER_CODE,
            status="soldout"
        ).update(status="pending")
        
        # 3. 신규/업데이트/삭제 분류
        new_products = []
        update_products = []
        all_options = []
        to_delete_ids = existing_ids - incoming_ids  # ✅ 전체파일에 없는 상품들만 삭제
        
        for item in products:
            pid = item["external_product_id"]
            options_data = item.pop("options")
            
            if pid in existing_map:
                # 기존 상품 업데이트
                product = existing_map[pid]
                for key, value in item.items():
                    setattr(product, key, value)
                update_products.append(product)
                stats.updated_products += 1
            else:
                # 신규 상품
                product = RawProduct(retailer=RETAILER_CODE, **item)
                new_products.append(product)
                stats.new_products += 1
            
            # 옵션 저장
            for option_data in options_data:
                all_options.append((pid, option_data))
        
        # 4. DB 작업 (트랜잭션)
        with transaction.atomic():
            # 신규 상품 등록
            if new_products:
                RawProduct.objects.bulk_create(new_products, batch_size=BATCH_SIZE)
                logger.info(f"신규 상품 등록: {len(new_products)}개")
            
            # 기존 상품 업데이트
            if update_products:
                RawProduct.objects.bulk_update(
                    update_products, 
                    fields=[k for k in item.keys()], 
                    batch_size=BATCH_SIZE
                )
                logger.info(f"기존 상품 업데이트: {len(update_products)}개")
            
            # ✅ 전체파일에 없는 상품 삭제 (전체파일일 때만)
            if to_delete_ids:
                updated_count = RawProduct.objects.filter(
                    external_product_id__in=to_delete_ids,
                    retailer=RETAILER_CODE
                ).update(status="soldout")

                logger.info(f"전체파일 기준 soldout 처리된 상품: {updated_count}개")
            
            # 모든 옵션 재등록
            RawProductOption.objects.filter(
                product__retailer=RETAILER_CODE
            ).delete()
            
            # 새 옵션 등록
            product_map = {p.external_product_id: p for p in 
                          RawProduct.objects.filter(external_product_id__in=incoming_ids, retailer=RETAILER_CODE)}
            
            options_to_create = []
            for pid, option_data in all_options:
                if pid in product_map:
                    options_to_create.append(RawProductOption(
                        product=product_map[pid],
                        option_name=option_data["option_name"],
                        external_option_id=option_data["external_option_id"],
                        stock=option_data["stock"],
                        price=option_data["price"]
                    ))
            
            if options_to_create:
                RawProductOption.objects.bulk_create(options_to_create, batch_size=BATCH_SIZE)
                logger.info(f"옵션 등록: {len(options_to_create)}개")
        
        stats.total_products = len(products)
        logger.info("전체 동기화 완료")
        
    except Exception as e:
        stats.add_error(f"전체 동기화 실패: {e}")
        raise

def register_partial_update(products, stats):
    """부분 업데이트 (부분파일 기준) - 삭제 없음"""
    try:
        logger.info("부분 업데이트 시작 - 상품 삭제 없이 추가/수정만")
        
        # 1. 기존 데이터 조회
        updating_product_ids = [p["external_product_id"] for p in products]
        existing_products = RawProduct.objects.filter(
            external_product_id__in=updating_product_ids,
            retailer=RETAILER_CODE
        )
        existing_map = {p.external_product_id: p for p in existing_products}
        
        # 2. 신규/업데이트 분류
        new_products = []
        update_products = []
        all_options = []
        
        for item in products:
            pid = item["external_product_id"]
            options_data = item.pop("options")
            
            if pid in existing_map:
                # 기존 상품 업데이트
                product = existing_map[pid]
                for key, value in item.items():
                    setattr(product, key, value)
                update_products.append(product)
                stats.updated_products += 1
            else:
                # 신규 상품
                product = RawProduct(retailer=RETAILER_CODE, **item)
                new_products.append(product)
                stats.new_products += 1
            
            # 옵션 저장
            for option_data in options_data:
                all_options.append((pid, option_data))
        
        # 3. DB 작업 (트랜잭션)
        with transaction.atomic():
            # 신규 상품 등록
            if new_products:
                RawProduct.objects.bulk_create(new_products, batch_size=BATCH_SIZE)
                logger.info(f"신규 상품 등록: {len(new_products)}개")
            
            # 기존 상품 업데이트
            if update_products:
                RawProduct.objects.bulk_update(
                    update_products, 
                    fields=[k for k in item.keys()], 
                    batch_size=BATCH_SIZE
                )
                logger.info(f"기존 상품 업데이트: {len(update_products)}개")
            
            # ✅ 업데이트되는 상품들의 기존 옵션만 삭제 (해당 상품의 옵션만)
            RawProductOption.objects.filter(
                product__external_product_id__in=updating_product_ids,
                product__retailer=RETAILER_CODE
            ).delete()
            
            # 새 옵션 등록
            product_map = {p.external_product_id: p for p in 
                          RawProduct.objects.filter(external_product_id__in=updating_product_ids, retailer=RETAILER_CODE)}
            
            options_to_create = []
            for pid, option_data in all_options:
                if pid in product_map:
                    options_to_create.append(RawProductOption(
                        product=product_map[pid],
                        option_name=option_data["option_name"],
                        external_option_id=option_data["external_option_id"],
                        stock=option_data["stock"],
                        price=option_data["price"]
                    ))
            
            if options_to_create:
                RawProductOption.objects.bulk_create(options_to_create, batch_size=BATCH_SIZE)
                logger.info(f"옵션 등록: {len(options_to_create)}개")
        
        stats.total_products += len(products)
        logger.info("부분 업데이트 완료")
        
    except Exception as e:
        stats.add_error(f"부분 업데이트 실패: {e}")
        raise

# ✅ FTP 및 파일 처리
def connect_ftp():
    """FTP 연결"""
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PSW)
        logger.info("FTP 연결 성공")
        return ftp
    except Exception as e:
        logger.error(f"FTP 연결 실패: {e}")
        raise

def get_files_to_process(ftp):
    """✅ 오늘 날짜 기준으로 처리할 파일 목록 결정"""
    try:
        today = date.today()
        
        # 1. 모든 CSV 파일 조회 및 분석
        all_files = [f for f in ftp.nlst() if f.endswith(".csv")]
        file_infos = []
        
        for filename in all_files:
            file_info = FileInfo(filename)
            if file_info.date:  # 날짜 파싱 성공한 파일만
                file_infos.append(file_info)
        
        # 2. 오늘 날짜 파일들만 필터링
        today_files = [f for f in file_infos if f.date == today]
        
        if not today_files:
            logger.info("오늘 날짜 파일이 없습니다.")
            return None, []
        
        # 3. 시간순, 시퀀스순 정렬
        today_files.sort(key=lambda x: x.sort_key)
        
        # 4. 전체파일과 부분파일 분리
        main_file = None
        partial_files = []
        
        for file_info in today_files:
            if file_info.is_main:
                main_file = file_info
            else:
                partial_files.append(file_info)
        
        # 5. 이미 처리된 파일들 확인
        processed_files = get_processed_files()
        processed_main_files = get_processed_main_files()
        
        # 6. 전체파일 처리 여부 확인
        main_to_process = None
        if main_file and main_file.filename not in processed_files:
            main_to_process = main_file
            logger.info(f"오늘 날짜 전체파일 발견: {main_file.filename}")
        elif today in processed_main_files:
            logger.info(f"오늘 날짜 전체파일 이미 처리됨: {processed_main_files[today]}")
        else:
            logger.info("오늘 날짜 전체파일 없음")
        
        # 7. 부분파일 처리 대상 결정
        partials_to_process = []
        
        if main_to_process:
            # 전체파일을 처리하는 경우: 전체파일보다 늦은 부분파일들만
            partials_to_process = [f for f in partial_files 
                                 if f.sort_key > main_to_process.sort_key 
                                 and f.filename not in processed_files]
        else:
            # 전체파일이 이미 처리된 경우: 마지막 처리된 파일 이후의 부분파일들만
            last_processed = get_last_processed_file_for_date(today, today_files)
            
            if last_processed:
                partials_to_process = [f for f in partial_files 
                                     if f.sort_key > last_processed.sort_key 
                                     and f.filename not in processed_files]
            else:
                # 아무것도 처리 안했으면 모든 부분파일
                partials_to_process = [f for f in partial_files 
                                     if f.filename not in processed_files]
        
        logger.info(f"처리 대상: 전체파일 {1 if main_to_process else 0}개, 부분파일 {len(partials_to_process)}개")
        
        return main_to_process, partials_to_process
        
    except Exception as e:
        logger.error(f"파일 목록 분석 실패: {e}")
        return None, []

def download_and_process_file(ftp, file_info, stats):
    """파일 다운로드 및 처리"""
    try:
        filename = file_info.filename
        
        # 파일 다운로드
        buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {filename}", buffer.write)
        buffer.seek(0)
        
        # CSV 파싱
        products = parse_csv(buffer.read(), stats)
        if not products:
            logger.warning(f"파일에서 유효한 상품을 찾을 수 없음: {filename}")
            return
        
        # 파일 타입에 따라 처리
        if file_info.is_main:
            logger.info(f"📥 전체파일 처리: {filename} ({len(products)}개 상품)")
            register_full_sync(products, stats)
            mark_main_processed(filename, file_info.date)
            stats.main_files_processed += 1
        else:
            logger.info(f"📥 부분파일 처리: {filename} ({len(products)}개 상품)")
            register_partial_update(products, stats)
            stats.partial_files_processed += 1
        
        # 처리 완료 표시
        mark_processed(filename)
        stats.processed_files += 1
        
    except Exception as e:
        stats.add_error(f"파일 처리 실패 ({filename}): {e}")

# ✅ 메인 실행 로직
def main():
    """메인 실행 함수"""
    stats = ProcessingStats()
    ftp = None
    
    try:
        logger.info("=== GNB 상품 동기화 시작 ===")
        logger.info(f"실행 날짜: {date.today()}")
        
        # FTP 연결
        ftp = connect_ftp()
        
        # ✅ 오늘 날짜 기준으로 처리할 파일 결정
        main_file, partial_files = get_files_to_process(ftp)
        
        if not main_file and not partial_files:
            logger.info("오늘 날짜에 처리할 새 파일이 없습니다.")
            return
        
        # ✅ 1단계: 전체파일 처리 (있는 경우)
        if main_file:
            try:
                logger.info(f"=== 전체파일 처리 시작 ===")
                download_and_process_file(ftp, main_file, stats)
                logger.info(f"=== 전체파일 처리 완료 ===")
            except Exception as e:
                stats.add_error(f"전체파일 처리 중 치명적 오류 ({main_file.filename}): {e}")
                logger.error("전체파일 처리 실패로 인해 부분파일 처리를 중단합니다.")
                return  # 전체파일 실패시 부분파일 처리 안함
        
        # ✅ 2단계: 부분파일 처리 (순서대로)
        if partial_files:
            logger.info(f"=== 부분파일 처리 시작 ({len(partial_files)}개) ===")
            for file_info in partial_files:
                try:
                    download_and_process_file(ftp, file_info, stats)
                except Exception as e:
                    # 개별 부분파일 실패는 다음 파일 계속 처리
                    stats.add_error(f"부분파일 처리 중 오류 ({file_info.filename}): {e}")
                    continue
            logger.info(f"=== 부분파일 처리 완료 ===")
        
    except Exception as e:
        stats.add_error(f"전체 처리 중 치명적 오류: {e}")
        
    finally:
        # FTP 연결 종료
        if ftp:
            try:
                ftp.quit()
            except:
                pass
        
        # ✅ 상세 결과 리포트
        summary = stats.get_summary()
        logger.info("=== 처리 결과 요약 ===")
        logger.info(f"실행 날짜: {date.today()}")
        logger.info(f"전체 처리 파일: {summary['processed_files']}개")
        logger.info(f"  └─ 전체파일: {summary['main_files_processed']}개")
        logger.info(f"  └─ 부분파일: {summary['partial_files_processed']}개")
        logger.info(f"총 상품: {summary['total_products']}개")
        logger.info(f"총 옵션: {summary['total_options']}개")
        logger.info(f"재고0 필터링: {summary['filtered_zero_stock']}개")
        logger.info(f"신규 상품: {summary['new_products']}개")
        logger.info(f"업데이트 상품: {summary['updated_products']}개")
        logger.info(f"삭제된 상품: {summary['deleted_products']}개")
        logger.info(f"소요 시간: {summary['duration']}")
        logger.info(f"오류 건수: {summary['error_count']}건")
        
        if stats.errors:
            logger.error("=== 오류 내역 ===")
            for error in stats.errors:
                logger.error(f"  - {error}")
        
        logger.info("=== GNB 상품 동기화 완료 ===")
        return stats.total_products  # ✅ 필수

if __name__ == "__main__":
    main()