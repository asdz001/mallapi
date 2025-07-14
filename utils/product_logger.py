# utils/product_logger.py

import logging
import os

# ✅ 로그 저장 디렉토리 설정 (요청에 따라 변경됨)
LOG_DIR = os.path.join(os.path.dirname(__file__), "../../log_backups/product_collect")
os.makedirs(LOG_DIR, exist_ok=True)

def get_product_logger(retailer_code: str) -> logging.Logger:
    """
    거래처 코드에 따라 logger를 생성하고 별도 로그 파일로 분리 저장
    :param retailer_code: 예: 'IT-G-03'
    :return: 해당 거래처 전용 Logger
    """
    logger_name = f"product_logger_{retailer_code}"
    logger = logging.getLogger(logger_name)

    # 이미 핸들러가 있으면 재사용
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    # 파일 저장 경로: log_backups/product_collect/{리테일코드}.log
    log_path = os.path.join(LOG_DIR, f"{retailer_code}.log")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")

    # 로그 포맷 설정
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
