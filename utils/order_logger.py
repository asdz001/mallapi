# mallapi/utils/order_logger.py

import os
import logging
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), "../log_backups")
os.makedirs(LOG_DIR, exist_ok=True)

# 전용 주문 로거
logger = logging.getLogger("order_logger")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, "order_send.log"), encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# ✅ JSON 저장 제거된 간단한 버전
def log_order_send(
    order_id,
    retailer_name,
    items,
    success=True,
    reason="",
    payload=None,
    response=None,
    error=None
):
    """
    주문 전송 요약 로그만 기록하는 함수 (개별 JSON 파일 저장 X)
    """
    status = "성공" if success else "실패"
    item_details = ", ".join([
        f"{item['sku']}({item['quantity']})[{item.get('product_id', '-')}]"
        for item in items
    ])

    # ✅ 로그 메세지 구성 (추가 정보 포함)
    log_msg = f"[{status}] 주문 ID: {order_id} / 거래처: {retailer_name} / 항목: {item_details} / 사유: {reason or '-'}"

    if payload:
        log_msg += f"\n📦 요청: {payload}"
    if response:
        log_msg += f"\n📥 응답: {response}"
    if error:
        log_msg += f"\n❌ 오류: {error}"

    logger.info(log_msg)
