# utils/bulk_update_logger.py

import logging
import os
from pathlib import Path
from datetime import datetime

def get_bulk_update_logger() -> logging.Logger:
    """
    벌크 업데이트 전용 로거 생성
    log_backups/bulk_update/bulk_update.log 파일에 저장
    :return: 벌크 업데이트 전용 Logger
    """
    logger_name = "bulk_update_logger"
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
            LOG_DIR = Path(settings.BASE_DIR) / "log_backups" / "bulk_update"
        else:
            raise ImportError("Django settings not available")
    except ImportError:
        # ✅ Django 환경이 아닐 때 - 절대 경로로 직접 지정
        LOG_DIR = Path(r"C:\Users\USER\myproject\mallapi\log_backups\bulk_update")
    
    # ✅ 디렉토리 생성
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 로그 파일 경로
    log_path = LOG_DIR / "bulk_update.log"
    
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
    logger.info(f"📝 벌크 업데이트 로거 초기화 완료: {log_path}")
    
    return logger


def log_start_session(logger, user=None, label: str = ""):
    """
    세션 시작 로그 출력 (예쁜 포맷)
    :param logger: 로거 객체
    :param user: 실행자 정보 (Django User 객체)
    :param label: 작업 라벨
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = f"📦 {label}" if label else ""
    user_info = f"👤 실행자: {user.username if user else 'System'}"
    
    logger.info("")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"🕒 실행 시작: {now} {label}")
    logger.info(user_info)
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("")


def log_end_session(logger, updated_count: int, total_time: float, success: bool = True):
    """
    세션 종료 로그 출력 (예쁜 포맷)
    :param logger: 로거 객체
    :param updated_count: 업데이트된 상품 수
    :param total_time: 총 소요 시간 (초)
    :param success: 성공 여부
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_icon = "✅" if success else "❌"
    status_text = "실행 완료" if success else "실행 실패"
    
    logger.info("")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"{status_icon} {status_text}: {now}")
    logger.info(f"📊 결과: {updated_count:,}개 상품 업데이트")
    logger.info(f"⏱️ 소요 시간: {total_time:.1f}초")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("")


def log_error_session(logger, error_message: str, total_time: float):
    """
    오류 발생 시 세션 종료 로그
    :param logger: 로거 객체
    :param error_message: 오류 메시지
    :param total_time: 총 소요 시간 (초)
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    logger.info("")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"❌ 실행 실패: {now}")
    logger.info(f"🚨 오류: {error_message}")
    logger.info(f"⏱️ 소요 시간: {total_time:.1f}초")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("")


def log_progress(logger, message: str):
    """
    진행상황 로그 (일반 메시지)
    :param logger: 로거 객체
    :param message: 로그 메시지
    """
    logger.info(message)
    print(message)  # 콘솔에도 출력