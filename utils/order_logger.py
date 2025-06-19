# mallapi/utils/order_logger.py

import os
import logging

# 로그를 저장할 위치 지정
LOG_DIR = os.path.join(os.path.dirname(__file__), "../log_backups")
os.makedirs(LOG_DIR, exist_ok=True)  # 폴더가 없으면 자동 생성

# 로그 설정
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "order_send.log"),  # 저장될 파일명
    level=logging.INFO,  # 로그 수준: INFO, ERROR 등
    format="%(asctime)s | %(levelname)s | %(message)s",  # 저장 형식
    encoding="utf-8"  # 한글 깨짐 방지
)

# 다른 파일에서 가져다 쓸 수 있도록 logger 변수 선언
logger = logging.getLogger("order_logger")
def log_order_send(order_id, retailer_name, items, success=True, reason=""):
    """
    주문 전송 로그 기록 함수
    :param order_id: 주문 ID
    :param retailer_name: 거래처 이름
    :param items: 주문 항목 리스트
    :param success: 전송 성공 여부
    :param reason: 실패 사유 (성공 시 빈 문자열)
    """
    item_details = ", ".join([f"{item['sku']}({item['quantity']})" for item in items])
    status = "성공" if success else "실패"
    
    logger.info(f"주문 전송 - ID: {order_id}, 거래처: {retailer_name}, 항목: {item_details}, 상태: {status}, 사유: {reason}")