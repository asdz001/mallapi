# mallapi/utils/order_logger.py

import os
import json
import logging
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), "../log_backups")
os.makedirs(LOG_DIR, exist_ok=True)

# 기본 로그 설정 (요약 로그)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "order_send.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

logger = logging.getLogger("order_logger")

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
    주문 전송 로그 기록 함수 (확장 버전)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    status = "성공" if success else "실패"
    item_details = ", ".join([
        f"{item['sku']}({item['quantity']})[{item.get('product_id', '-')}]"
        for item in items
    ])

    # 1) 요약 로그 → order_send.log
    logger.info(f"[{status}] 주문 ID: {order_id} / 거래처: {retailer_name} / 항목: {item_details} / 사유: {reason}")

    # 2) 상세 로그 → 개별 파일
    log_data = {
        "timestamp": timestamp,
        "order_id": order_id,
        "retailer_name": retailer_name,
        "status": status,
        "reason": reason,
        "items": items,
    }

    if payload:
        log_data["payload"] = payload

    if response:
        log_data["response"] = response

    if error:
        log_data["error"] = error

    log_filename = os.path.join(LOG_DIR, f"order_{order_id}_{timestamp}.json")
    with open(log_filename, "w", encoding="utf-8") as f:
        f.write(json.dumps(log_data, indent=2, ensure_ascii=False))
