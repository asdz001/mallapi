"""
비에띠 (IT-V-02) 주문 전송 모듈
==============================
🏢 드레스코드 API를 사용하는 비에띠 부티크 전용
📋 order_service.py ↔ dresscode_base.py 연결 역할
"""

from shop.models import Order
from .dresscode_base import DresscodeBaseClient

# 🔑 비에띠 전용 API 설정 (거래처별 변동 정보만)
GAUDENZI_CONFIG = {
    'client': 'vietti',
    'channel_key': 'cd38797c-44b8-43a1-8591-92ab7b61f1d8',
    'subscription_key': 'd9b2538817b248d6a39e7289d5b87e87',
    'retailer_code': 'IT-V-02',
    'test_mode': False  # 🔧 TODO: 운영시 False로 변경
}


def send_order(order: Order):
    """
    비에띠 주문 전송 함수 (order_service.py에서 호출)
    
    Args:
        order: Django Order 객체
        
    Returns:
        List[Dict]: [{"sku": "", "item_id": "", "success": bool, "reason": ""}]
    """
    # 🔧 드레스코드 베이스 클라이언트 초기화 및 전송
    client = DresscodeBaseClient(GAUDENZI_CONFIG)
    return client.send_order(order)