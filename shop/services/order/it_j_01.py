"""
줄리안 (IT-J-01) 주문 전송 모듈
==============================
🏢 드레스코드 API를 사용하는 줄리안 부티크 전용
📋 order_service.py ↔ dresscode_base.py 연결 역할
"""
#줄리안은 현재 개발이 되어있지않아 운영 안되어 테스트모드로 전송


from shop.models import Order
from .dresscode_base import DresscodeBaseClient

# 🔑 줄리안 전용 API 설정 (거래처별 변동 정보만)
GAUDENZI_CONFIG = {
    'client': 'julian',
    'channel_key': '54536dc3-6fda-4bdd-8f3b-3213c5aae66d',
    'subscription_key': 'd9b2538817b248d6a39e7289d5b87e87',
    'retailer_code': 'IT-J-01',
    'test_mode': True  # 🔧 TODO: 운영시 False로 변경
}


def send_order(order: Order):
    """
    줄리안 주문 전송 함수 (order_service.py에서 호출)
    
    Args:
        order: Django Order 객체
        
    Returns:
        List[Dict]: [{"sku": "", "item_id": "", "success": bool, "reason": ""}]
    """
    # 🔧 드레스코드 베이스 클라이언트 초기화 및 전송
    client = DresscodeBaseClient(GAUDENZI_CONFIG)
    return client.send_order(order)