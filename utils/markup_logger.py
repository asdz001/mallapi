# mallapi/utils/markup_logger.py
# 마크업 관련 로깅 전용 모듈

import os
import logging
from datetime import datetime

# 로그 디렉토리 설정 (order_logger.py와 동일한 위치)
LOG_DIR = os.path.join(os.path.dirname(__file__), "../log_backups")
os.makedirs(LOG_DIR, exist_ok=True)

# 마크업 전용 로거 설정
markup_logger = logging.getLogger("markup_logger")
markup_logger.setLevel(logging.INFO)

if not markup_logger.handlers:
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, "markup_debug.log"), encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler.setFormatter(formatter)
    markup_logger.addHandler(file_handler)


def log_markup_failure(product, reason, details="", search_process=None):
    """
    마크업 계산 실패 로그 기록
    
    Args:
        product: 상품 객체
        reason (str): 실패 이유
        details (str): 상세 정보
        search_process (list): 검색 과정 리스트 (선택사항)
    """
    product_id = getattr(product, 'id', 'Unknown')
    
    # 기본 상품 정보
    product_info = {
        'id': product_id,
        'retailer': getattr(product, 'retailer', 'Unknown'),
        'brand': getattr(product, 'raw_brand_name', 'Unknown'),
        'season': getattr(product, 'season', 'Unknown'),
        'gender': getattr(product, 'gender', 'Unknown'),
        'category': getattr(product, 'category1', 'Unknown')
    }
    
    # 로그 메시지 구성
    log_msg = f"[마크업 계산 실패] 상품 ID: {product_id} | 이유: {reason}"
    log_msg += f"\n📦 상품정보: 거래처={product_info['retailer']} | 브랜드={product_info['brand']} | 시즌={product_info['season']} | 성별={product_info['gender']} | 카테고리={product_info['category']}"
    
    if details:
        log_msg += f"\n📋 상세정보: {details}"
    
    if search_process:
        log_msg += f"\n🔍 검색과정: {' → '.join(search_process)}"
    
    markup_logger.error(log_msg)


def log_excel_upload_failure(row_number, row_data, reason, details=""):
    """
    엑셀 대량등록 실패 로그 기록
    
    Args:
        row_number (int): 실패한 행 번호
        row_data (dict): 행 데이터
        reason (str): 실패 이유
        details (str): 상세 정보
    """
    # 행 데이터에서 주요 정보 추출
    retailer_code = row_data.get('거래처코드', 'Unknown')
    brand_name = row_data.get('브랜드명', 'Unknown')
    season = row_data.get('시즌', 'Unknown')
    gender = row_data.get('성별', 'Unknown')
    category = row_data.get('카테고리', 'Unknown')
    markup = row_data.get('마크업', 'Unknown')
    
    # 로그 메시지 구성
    log_msg = f"[엑셀 업로드 실패] 행번호: {row_number} | 이유: {reason}"
    log_msg += f"\n📦 입력데이터: 거래처={retailer_code} | 브랜드={brand_name} | 시즌={season} | 성별={gender} | 카테고리={category} | 마크업={markup}"
    
    if details:
        log_msg += f"\n📋 상세정보: {details}"
    
    # 전체 행 데이터도 기록 (디버깅용)
    log_msg += f"\n📄 전체데이터: {row_data}"
    
    markup_logger.error(log_msg)


def log_excel_upload_summary(total_rows, created, updated, skipped, failed_count, file_name=""):
    """
    엑셀 대량등록 결과 요약 로그 기록
    
    Args:
        total_rows (int): 전체 행 수
        created (int): 생성된 수
        updated (int): 수정된 수  
        skipped (int): 건너뛴 수
        failed_count (int): 실패한 수
        file_name (str): 업로드된 파일명
    """
    log_msg = f"[엑셀 업로드 완료] 파일: {file_name}"
    log_msg += f"\n📊 처리결과: 전체={total_rows}행 | 생성={created}개 | 수정={updated}개 | 건너뜀={skipped}개 | 실패={failed_count}개"
    
    if failed_count > 0:
        log_msg += f"\n⚠️ 실패건수가 {failed_count}개 있습니다. 상세 내용은 위의 개별 실패 로그를 확인하세요."
    
    markup_logger.info(log_msg)


def log_markup_success(product, markup_value, brand_setting_info=""):
    """
    마크업 계산 성공 로그 기록 (선택적 사용)
    
    Args:
        product: 상품 객체
        markup_value (float): 계산된 마크업 값
        brand_setting_info (str): 적용된 브랜드 설정 정보
    """
    product_id = getattr(product, 'id', 'Unknown')
    
    log_msg = f"[마크업 계산 성공] 상품 ID: {product_id} | 마크업: {markup_value}"
    
    if brand_setting_info:
        log_msg += f" | 적용설정: {brand_setting_info}"
    
    markup_logger.info(log_msg)


def log_brand_setting_validation_error(retailer_code, brand_name, seasons, priority, reason):
    """
    브랜드 설정 검증 오류 로그 기록
    
    Args:
        retailer_code (str): 거래처 코드
        brand_name (str): 브랜드명
        seasons (str): 시즌
        priority (int): 우선순위
        reason (str): 오류 이유
    """
    log_msg = f"[브랜드 설정 검증 오류] 거래처: {retailer_code} | 브랜드: {brand_name} | 시즌: {seasons} | 우선순위: {priority}"
    log_msg += f"\n❌ 오류내용: {reason}"
    
    markup_logger.warning(log_msg)


def log_markup_search_debug(product, search_steps):
    """
    마크업 검색 과정 상세 디버그 로그 (개발용)
    
    Args:
        product: 상품 객체
        search_steps (list): 검색 단계별 정보
    """
    product_id = getattr(product, 'id', 'Unknown')
    
    log_msg = f"[마크업 검색 디버그] 상품 ID: {product_id}"
    
    for i, step in enumerate(search_steps, 1):
        log_msg += f"\n  {i}단계: {step}"
    
    markup_logger.debug(log_msg)