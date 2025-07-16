"""
드레스코드 API 공통 베이스 클래스 (러프 틀)
========================================
🏢 모든 드레스코드 거래처에서 공통으로 사용하는 베이스 클래스
📋 각 거래처별 설정값을 받아서 공통 로직 처리
"""

import requests
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from shop.models import Order, OrderItem


# 📮 밀라네제 고정 주소 정보 (모든 드레스코드 거래처 공통 사용)
MILANESE_ADDRESS = {
    "billing": {
        "name": "",
        "surname": "",
        "email": "md@milanese.co.kr",
        "streetName": "JOJUNGDAE-RO",
        "streetNumber": "F1025, 45",
        "city": "HANAM-SI",
        "zip": "12918",
        "state": "GYEONGGI-DO",
        "country": "KR",
        "phone": "01073360902",
        "mobile": "01073360902",
        "businessName": "MILANESE KOREA CO LTD",
        "vatNumber": "6178605369",
        "notes": "Milanese Korea - Main Office"
    },
    "shipping": {
        "name": "",
        "surname": "",
        "email": "md@milanese.co.kr",
        "streetName": "JOJUNGDAE-RO",
        "streetNumber": "F1025, 45", 
        "city": "HANAM-SI",
        "zip": "12918",
        "state": "GYEONGGI-DO",
        "country": "KR",
        "phone": "01073360902",
        "mobile": "01073360902",
        "businessName": "MILANESE KOREA CO LTD",
        "notes": "Milanese Korea - Shipping Address"
    }
}

# 🔧 디버깅 모드 (운영시 False로 변경)
DEBUG_MODE = True

def debug_print(message):
    """디버깅용 출력 (운영시 쉽게 제거 가능)"""
    if DEBUG_MODE:
        print(f"🔍 [DRESSCODE] {message}")


class DresscodeBaseClient:
    """드레스코드 API 공통 베이스 클래스"""
    
    def __init__(self, config: Dict):
        """
        초기화
        
        Args:
            config: 거래처별 설정 딕셔너리
            {
                'client': 'gaudenzi',
                'channel_key': '33a2aaeb-7ef2-44c5-bb66-0d3a84e9869f',
                'subscription_key': 'd9b2538817b248d6a39e7289d5b87e87',
                'retailer_code': 'IT-G-03',
                'test_mode': True  # 🔧 TODO: 운영시 False로 변경
            }
        """
        self.config = config
        self.client = config['client']
        self.channel_key = config['channel_key']
        self.subscription_key = config['subscription_key']
        self.retailer_code = config['retailer_code']
        self.test_mode = config.get('test_mode', True)  # 🔧 기본값: 테스트 모드
        
        # 🌐 드레스코드 API 엔드포인트 (공식 문서 기반)
        self.base_url = "https://api.dresscode.cloud"
        self.order_endpoint = f"{self.base_url}/channels/v2/api/feeds/en/clients/{self.client}/orders/items"
        
        debug_print(f"클라이언트 초기화: {self.client} (테스트모드: {self.test_mode})")
    
    def get_headers(self) -> Dict[str, str]:
        """API 호출용 헤더 생성"""
        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        debug_print(f"헤더 생성 완료: {list(headers.keys())}")
        return headers
    
    def get_params(self) -> Dict[str, str]:
        """API 호출용 파라미터 생성"""
        params = {
            'channelKey': self.channel_key
        }
        debug_print(f"파라미터 생성 완료: {params}")
        return params
    
    def build_order_item_data(self, order_item: OrderItem, channel_order_id: str) -> Dict:
        """
        OrderItem을 드레스코드 API 형식으로 변환
        
        Args:
            order_item: Django OrderItem 객체
            channel_order_id: 고유 채널 주문 ID (self.order.id-self.id 사용)
            
        Returns:
            드레스코드 API 요청 데이터
        """
        debug_print(f"주문 항목 데이터 빌드 시작: {order_item.id}")
        
        # 🔧 실제 드레스코드 상품 ID 매핑
        product_id = order_item.product.external_product_id
        if not product_id:
            debug_print(f"❌ 상품 ID 없음: {order_item.product.id}")
            raise ValueError(f"상품 {order_item.product.id}에 external_product_id가 없습니다")
        
        # 🔧 수정: 옵션 가격 우선 사용, 없으면 상품 원가 사용
        unit_price = float(order_item.option.price or order_item.price_org or 0)
        debug_print(f"사용할 가격: 옵션가격={order_item.option.price}, 상품원가={order_item.price_org}, 최종={unit_price}")
        
        # 📦 기본 주문 데이터
        order_data = {
            "channelOrderID": channel_order_id,  # 🔧 수정: self.order.id-self.id 사용
            "productID": product_id,
            "size": order_item.option.option_name,
            "soldUnits": order_item.quantity,
            "unitSellingPrice": unit_price,  # 🔧 수정: 옵션 가격 우선 사용
            "channelOrderCreated": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "channelOrderStatus": "created",
            "administrativeNotes": f"Order from MALL system - {self.retailer_code}",
            "billingAddress": MILANESE_ADDRESS["billing"],
            "shippingAddress": MILANESE_ADDRESS["shipping"]
        }
        
        # 🔧 수정: 테스트 모드일 때만 testMode 필드 추가
        if self.test_mode:
            order_data["testMode"] = True
            debug_print("테스트 모드 필드 추가됨")
        
        debug_print(f"주문 데이터 빌드 완료: {channel_order_id}")
        return order_data
    
    def create_order_item_api(self, order_data: Dict) -> Dict:
        """
        드레스코드 API에 주문 항목 전송
        
        Args:
            order_data: 주문 데이터
            
        Returns:
            API 응답 결과 딕셔너리
        """
        debug_print(f"API 호출 시작: {order_data.get('channelOrderID')}")
        
        try:
            # 📤 API 호출
            response = requests.post(
                self.order_endpoint,
                params=self.get_params(),
                json=order_data,
                headers=self.get_headers(),
                timeout=30
            )
            
            debug_print(f"API 응답 코드: {response.status_code}")
            
            # 📨 응답 처리
            return self.process_api_response(response, order_data)
            
        except requests.exceptions.RequestException as e:
            debug_print(f"❌ API 요청 실패: {e}")
            return {
                'success': False,
                'error': 'API_REQUEST_FAILED',
                'message': str(e),
                'order_data': order_data
            }
        except Exception as e:
            debug_print(f"❌ 예상치 못한 오류: {e}")
            return {
                'success': False,
                'error': 'UNEXPECTED_ERROR',
                'message': str(e),
                'order_data': order_data
            }
    
    def process_api_response(self, response: requests.Response, order_data: Dict) -> Dict:
        """
        드레스코드 API 응답 처리
        
        Args:
            response: requests 응답 객체
            order_data: 원본 주문 데이터
            
        Returns:
            처리 결과 딕셔너리
        """
        result = {
            'success': False,
            'status_code': response.status_code,
            'order_data': order_data,
            'endpoint': self.order_endpoint
        }
        
        try:
            # 📄 JSON 응답 파싱
            response_data = response.json()
            result['response_data'] = response_data
            
            debug_print(f"응답 데이터: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            
            if response.status_code == 200:
                result['success'] = True
                result['message'] = 'OrderItem이 성공적으로 생성되었습니다'
                result['order_status'] = 'SENT'  # 🔧 성공시 상태
                
                # 새로 생성된 OrderItem ID 추출 (문서 기준)
                if 'data' in response_data and 'code' in response_data['data']:
                    result['order_item_id'] = response_data['data']['code']
                    debug_print(f"✅ 생성된 OrderItem ID: {result['order_item_id']}")
                    
            else:
                # 🔧 실패 응답 처리 - 품절 vs 일반 오류 구분
                error_detail = self.extract_error_detail(response_data)
                result['message'] = error_detail
                
                # 🔧 TODO: 실제 드레스코드 API 응답 확인 후 수정 필요
                # 품절 관련 키워드를 실제 응답 메시지에 맞게 업데이트하세요
                if self.is_soldout_error(error_detail):
                    result['order_status'] = 'SOLDOUT'
                    debug_print(f"🔍 품절 감지: {error_detail}")
                else:
                    result['order_status'] = 'FAILED'
                    debug_print(f"❌ 일반 오류: {error_detail}")
                
        except json.JSONDecodeError:
            result['response_text'] = response.text
            result['error'] = 'INVALID_JSON_RESPONSE'
            result['message'] = 'JSON 응답을 파싱할 수 없습니다'
            result['order_status'] = 'FAILED'
            debug_print(f"❌ JSON 파싱 실패: {response.text[:200]}")
            
        return result
    
    def extract_error_detail(self, response_data: Dict) -> str:
        """
        API 응답에서 에러 메시지 추출
        
        Args:
            response_data: API 응답 JSON 데이터
            
        Returns:
            에러 메시지 문자열
        """
        # 🔧 드레스코드 API 응답 구조에 맞춘 에러 메시지 추출
        if isinstance(response_data, dict):
            # 에러 응답의 detail 필드 확인
            if 'error' in response_data and isinstance(response_data['error'], dict):
                error_obj = response_data['error']
                if 'detail' in error_obj:
                    return str(error_obj['detail'])
                elif 'title' in error_obj:
                    return str(error_obj['title'])
            
            # 일반적인 message 필드 확인
            if 'message' in response_data:
                return str(response_data['message'])
            
            # data 내부의 detail 확인
            if 'data' in response_data and isinstance(response_data['data'], dict):
                if 'detail' in response_data['data']:
                    return str(response_data['data']['detail'])
        
        return "알 수 없는 오류가 발생했습니다"
    
    def is_soldout_error(self, error_message: str) -> bool:
        """
        에러 메시지를 분석하여 품절 오류인지 판단
        
        Args:
            error_message: API에서 받은 에러 메시지
            
        Returns:
            품절 오류 여부 (True: 품절, False: 일반 오류)
        """
        # 🔧 TODO: 실제 드레스코드 API 품절 응답 확인 후 키워드 업데이트
        # 현재는 일반적인 품절 관련 키워드들로 설정
        # 실제 테스트 후 아래 키워드들을 실제 응답 메시지에 맞게 수정하세요
        
        soldout_keywords = [
            # 🔧 추후 수정: 실제 드레스코드 품절 응답 메시지로 변경
            "STOCK_NOT_AVAILABLE",      # 재고 없음
            "OUT_OF_STOCK",             # 품절
            "SOLDOUT",                  # 품절
            "INSUFFICIENT_STOCK",       # 재고 부족
            "NOT_AVAILABLE",            # 구매 불가
            "PRODUCT_NOT_FOUND",        # 상품 없음 (품절로 인한)
            "ITEM_NOT_FOUND",           # 아이템 없음
            "UNAVAILABLE",              # 구매 불가
            "NO_STOCK",                 # 재고 없음
            # 🔧 TODO: 실제 API 테스트 후 추가 키워드 발견시 여기에 추가
        ]
        
        error_upper = error_message.upper()
        is_soldout = any(keyword in error_upper for keyword in soldout_keywords)
        
        if is_soldout:
            debug_print(f"🔍 품절 키워드 감지: '{error_message}' 에서 품절 관련 키워드 발견")
        
        return is_soldout
    
    def get_error_message(self, status_code: int, response_data: Dict) -> str:
        """
        HTTP 상태 코드와 응답 데이터를 기반으로 에러 메시지 생성
        
        🔧 TODO: 실제 드레스코드 API 응답에 맞게 수정 필요
        """
        error_messages = {
            400: "잘못된 요청 데이터입니다",
            401: "인증에 실패했습니다",
            403: "권한이 없습니다",
            404: "리소스를 찾을 수 없습니다",
            429: "요청 제한을 초과했습니다",
            500: "서버 내부 오류입니다"
        }
        
        base_message = error_messages.get(status_code, f"예상치 못한 HTTP 오류: {status_code}")
        
        # 🔧 응답 데이터에서 상세 오류 메시지 추출 (실제 구조에 맞게 수정)
        if isinstance(response_data, dict):
            if 'error' in response_data and 'detail' in response_data['error']:
                base_message += f" - {response_data['error']['detail']}"
            elif 'message' in response_data:
                base_message += f" - {response_data['message']}"
        
        return base_message
    
    def send_order(self, order: Order) -> List[Dict]:
        """
        주문을 드레스코드 API로 전송 (메인 함수)
        
        Args:
            order: Django Order 객체
            
        Returns:
            결과 리스트 (it_b_01.py와 동일한 형식)
            [{"sku": "", "item_id": "", "success": bool, "reason": ""}]
        """
        debug_print(f"주문 전송 시작: Order #{order.id} ({self.client})")

        
        results = []
        payloads = []
        responses = []
        successful_count = 0
        failed_count = 0
        
        # 📦 각 주문 항목을 개별적으로 처리
        order_items = order.items.all()
        debug_print(f"처리할 주문 항목 수: {len(order_items)}")
        
        for index, order_item in enumerate(order_items):
            try:
                debug_print(f"항목 {index + 1}/{len(order_items)} 처리 중...")
                
                # 🔖 채널 주문 ID는 self.order.id-self.id 사용
                channel_order_id = f"{order.id}-{order_item.id}"
                if not channel_order_id:
                    debug_print(f"❌ self.order.id-self.id 없음: {order_item.id}")
                    raise ValueError(f"OrderItem {order_item.id}에 self.order.id-self.id 가 없습니다")
                
                debug_print(f"매핑 확인 - channelOrderID: {channel_order_id}, sku(external_option_id): {order_item.option.external_option_id}")
                
                # 📦 주문 데이터 빌드 (주소 정보는 자동으로 포함됨)
                order_data = self.build_order_item_data(order_item, channel_order_id)
                
                # 📤 API 전송
                api_result = self.create_order_item_api(order_data)
                payloads.append(order_data if 'order_data' in locals() else {})
                responses.append(api_result)

                
                # 📋 결과 처리 - 상태 분류 포함
                if api_result['success']:
                    successful_count += 1
                    result = {
                        "sku": order_item.option.external_option_id,
                        "item_id": order_item.id,
                        "success": True,
                        "reason": ""
                    }
                    debug_print(f"✅ 항목 {index + 1} 전송 성공")
                else:
                    failed_count += 1
                    # 🔧 상태별 분류 (품절 vs 일반 오류)
                    order_status = api_result.get('order_status', 'FAILED')
                    result = {
                        "sku": order_item.option.external_option_id,
                        "item_id": order_item.id,
                        "success": False,
                        "reason": api_result.get('message', 'Unknown error'),
                        "order_status": order_status  # 🔧 SOLDOUT, FAILED 구분
                    }
                    
                    if order_status == 'SOLDOUT':
                        debug_print(f"🔍 항목 {index + 1} 품절: {result['reason']}")
                    else:
                        debug_print(f"❌ 항목 {index + 1} 전송 실패: {result['reason']}")
                
                results.append(result)
  
                
            except Exception as e:
                failed_count += 1
                error_message = f"항목 처리 중 오류: {str(e)}"
                debug_print(f"❌ {error_message}")
                
                result = {
                    "sku": order_item.option.external_option_id if order_item.option else "UNKNOWN",
                    "item_id": order_item.id,
                    "success": False,
                    "reason": error_message,
                    "order_status": "FAILED"  # 🔧 예외 발생시 일반 실패로 처리
                }
                results.append(result)
                payloads.append(order_data)
                responses.append(str(e))
        
        # 📊 최종 결과 로깅
        debug_print(f"전송 완료: 성공 {successful_count}개, 실패 {failed_count}개")
        
        
        
        return results, payloads, responses