# utils/product_logger.py

import logging
import os
from pathlib import Path
from datetime import datetime



# 거래처별 로거 생성 함수
def get_product_logger(retailer_code: str) -> logging.Logger:
    """
    거래처 코드에 따라 logger를 생성하고 별도 로그 파일로 분리 저장
    :param retailer_code: 예: 'IT-G-03'
    :return: 해당 거래처 전용 Logger
    """
    logger_name = f"product_logger_{retailer_code}"
    logger = logging.getLogger(logger_name)

    # ✅ 핸들러 중복 방지 - 이미 설정된 경우 기존 것 사용
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)
    
    # ✅ 상위 로거로 전파 방지 (중복 출력 방지)
    logger.propagate = False

    # ✅ 정확한 경로 설정 - MALLAPI 폴더 내부
    try:
        # Django 환경에서 실행될 때
        from django.conf import settings
        if hasattr(settings, 'BASE_DIR'):
            # settings.BASE_DIR은 이미 C:\Users\USER\myproject\mallapi를 가리킴
            LOG_DIR = Path(settings.BASE_DIR) / "log_backups" / "product_collect"
        else:
            raise ImportError("Django settings not available")
    except ImportError:
        # ✅ Django 환경이 아닐 때 - 절대 경로로 직접 지정
        LOG_DIR = Path(r"C:\Users\USER\myproject\mallapi\log_backups\product_collect")
    
    # ✅ 디렉토리 생성
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 로그 파일 경로
    log_path = LOG_DIR / f"{retailer_code}.log"
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    
    # 콘솔 핸들러 (실시간 확인용)
    console_handler = logging.StreamHandler()

    # 포맷터 설정
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # ✅ 로거 생성 확인 로그 (파일 경로 포함)
    logger.info(f"📝 로거 초기화 완료: {log_path}")
    
    return logger


# Session 시작 로그 출력 함수
def log_session_separator(logger, label: str = ""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = f"📦 {label}" if label else ""
    logger.info("")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"🕒 실행 시작: {now} {label}")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("")