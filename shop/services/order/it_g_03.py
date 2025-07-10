"""
가우덴찌 (IT-G-03) 주문 전송 모듈
==============================
🏢 드레스코드 API를 사용하는 가우덴찌 부티크 전용
📋 order_service.py ↔ dresscode_base.py 연결 역할
"""

from shop.models import Order
from .dresscode_base import DresscodeBaseClient

# 🔑 가우덴찌 전용 API 설정 (거래처별 변동 정보만)
GAUDENZI_CONFIG = {
    'client': 'gaudenzi',
    'channel_key': '33a2aaeb-7ef2-44c5-bb66-0d3a84e9869f',
    'subscription_key': 'd9b2538817b248d6a39e7289d5b87e87',
    'retailer_code': 'IT-G-03',
    'test_mode': False  # 🔧 TODO: 운영시 False로 변경
}


def send_order(order: Order):
    """
    가우덴찌 주문 전송 함수 (order_service.py에서 호출)
    
    Args:
        order: Django Order 객체
        
    Returns:
        List[Dict]: [{"sku": "", "item_id": "", "success": bool, "reason": ""}]
    """
    # 🔧 드레스코드 베이스 클라이언트 초기화 및 전송
    client = DresscodeBaseClient(GAUDENZI_CONFIG)
    return client.send_order(order)