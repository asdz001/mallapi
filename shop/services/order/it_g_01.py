"""
지앤비 (IT-G-01) B2B 주문 전송 모듈 - 최종 운영 버전
========================================================
🏢 BeeStore SOAP API를 사용하는 지앤비 부티크 전용
📋 order_service.py에서 호출되는 주문 전송 함수
🔧 직접 XML SOAP 요청 방식 (zeep 우회)
"""

import requests
from datetime import datetime
from decimal import Decimal
from shop.models import Order
from utils.order_logger import log_order_send

# 🔑 지앤비 전용 BeeStore API 설정
GNB_CONFIG = {
    'soap_endpoint': 'http://93.46.41.5:8180/milaneseb2b/soapBeestore.php',
    'user': 'milaneseb2b',
    'password': 'w8Yc$K',
    'igu_negozio': '179',
    'igu_cliente': '13\\4\\3\\6867\\242476\\0',  # 백슬래시 형식 (성공 확인됨)
    'cod_iva': 'NI08',
    'retailer_name': 'GNB(지앤비)',
    'retailer_code': 'IT-G-01'
}


def send_order(order: Order):
    """
    지앤비 B2B 주문 전송 함수 (order_service.py에서 호출)
    
    Args:
        order: Django Order 객체
        
    Returns:
        Tuple: (results, payload_data, response_data)
               - results: List[Dict] 각 주문 항목별 성공/실패 결과
               - payload_data: Dict 전송된 SOAP XML 데이터
               - response_data: Dict 받은 응답 데이터
    """
    
    results = []
    payload_data = {}
    response_data = {}
    
    # 📦 주문 항목별 정보 수집 및 초기화
    items_info = []
    for item in order.items.all():
        item_info = {
            'item_id': item.id,
            'sku': item.option.external_option_id,
            'quantity': item.quantity,
            'product_id': item.product.id
        }
        items_info.append(item_info)
        
        # 결과 리스트 초기화 (order_service.py 형식에 맞춤)
        results.append({
            "sku": item.option.external_option_id,
            "item_id": item.id,
            "success": False,
            "reason": "",
            "stock": -1  # BeeStore는 재고 정보 별도 제공 안함
        })
    
    # 🔧 단일 상품만 처리 (BeeStore API 제한사항)
    if not order.items.exists():
        error_msg = "주문 항목이 없음"
        log_order_send(
            order.id, GNB_CONFIG['retailer_name'], [],
            success=False, reason=error_msg
        )
        return results, payload_data, {"error": error_msg}
    
    first_item = order.items.first()
    
    try:
        # 📋 SOAP XML 구성
        soap_xml = _build_soap_xml(order, first_item)
        
        # 📝 페이로드 데이터 저장 (로그용)
        payload_data = {
            "soap_endpoint": GNB_CONFIG['soap_endpoint'],
            "method": "fInserimentoDocumento",
            "order_id": order.id,
            "item_id": first_item.id,
            "product_code": first_item.option.external_option_id,
            "quantity": first_item.quantity,
            "price_retail": float(first_item.product.price_retail or Decimal("0.0")),
            "price_net": float(first_item.option.price or Decimal("0.0")),
            "xml_size": len(soap_xml),
            "headers": {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'urn:fInserimentoDocumentoAction'
            }
        }
        
        # 📤 SOAP 요청 전송
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'urn:fInserimentoDocumentoAction'
        }
        
        response = requests.post(
            GNB_CONFIG['soap_endpoint'],
            data=soap_xml.encode('utf-8'),
            headers=headers,
            timeout=30
        )
        
        # 📥 응답 처리
        success, document_id, error_msg = _parse_soap_response(response)
        
        # 📝 응답 데이터 저장 (로그용)
        response_data = {
            "http_status": response.status_code,
            "response_size": len(response.content),
            "success": success,
            "document_id": document_id if success else None,
            "error_message": error_msg if not success else None,
            "raw_response": response.text[:500] + "..." if len(response.text) > 500 else response.text
        }
        
        if success:
            # ✅ 성공 처리
            reason = f"주문 생성 성공 (문서ID: {document_id})"
            
            # 결과 업데이트
            for i, result in enumerate(results):
                if i == 0:  # 첫 번째 항목만 성공
                    result["success"] = True
                    result["reason"] = reason
                else:  # 나머지는 미처리 (BeeStore API 제한)
                    result["success"] = False
                    result["reason"] = "단일 상품만 처리됨 (BeeStore 제한)"
            
            # 📝 성공 로그
            log_order_send(
                order.id, GNB_CONFIG['retailer_name'], items_info,
                success=True, reason=reason, 
                payload=payload_data, response=response_data
            )
            
        else:
            # ❌ 실패 처리
            _handle_order_failure(results, error_msg, items_info, order.id, payload_data, response_data)
            
    except Exception as e:
        # ❌ 예외 처리
        error_msg = f"SOAP 요청 오류: {str(e)}"
        
        # 예외 응답 데이터 저장
        response_data = {
            "success": False,
            "error_type": type(e).__name__,
            "error_message": str(e)
        }
        
        _handle_order_failure(results, error_msg, items_info, order.id, payload_data, response_data)
    
    # ✅ 3개 값 반환 (order_service.py 형식에 맞춤)
    return results, payload_data, response_data


def _build_soap_xml(order, item):
    """
    BeeStore fInserimentoDocumento용 SOAP XML 구성
    
    Args:
        order: Django Order 객체
        item: OrderItem 객체 (첫 번째 항목)
        
    Returns:
        str: SOAP XML 문자열
    """
    
    # 주문 번호 처리 (item.id 사용 - 문서 요구사항에 따라 정수형)
    num_rif = item.id
    
    # 날짜 형식 (YYYY-MM-DD)
    dt_rif = order.created_at.strftime('%Y-%m-%d')
    
    # 가격 정보 처리
    price_retail = float(item.product.price_retail or Decimal("0.0"))
    price_net = float(item.option.price or Decimal("0.0"))
    
    soap_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:wsBeestore">
    <soapenv:Body>
        <urn:fInserimentoDocumento>
            <user>{GNB_CONFIG['user']}</user>
            <password>{GNB_CONFIG['password']}</password>
            <inserimentoDocumento>
                <testata>
                    <iguNegozio>{GNB_CONFIG['igu_negozio']}</iguNegozio>
                    <iguNegozioDest></iguNegozioDest>
                    <dtRif>{dt_rif}</dtRif>
                    <numRif>{num_rif}</numRif>
                    <iguTipoDocumento>B2BORD</iguTipoDocumento>
                    <iguCliente>{GNB_CONFIG['igu_cliente']}</iguCliente>
                    <tessera></tessera>
                    <nominativo>MILANESE</nominativo>
                    <indirizzo>JOJUNGDAE-RO F1025, 45</indirizzo>
                    <citta>HANAM-SI</citta>
                    <cap>12918</cap>
                    <provincia>GYEONGGI-DO</provincia>
                    <telefono>01073360902</telefono>
                    <codiceStato>KOR</codiceStato>
                    <partitaIva>6178605369</partitaIva>
                    <codFisc>6178605369</codFisc>
                </testata>
                <righe>
                    <codArticolo>{item.option.external_option_id}</codArticolo>
                    <quantitaMov>{item.quantity}</quantitaMov>
                    <przVenditaLordo>{price_retail}</przVenditaLordo>
                    <sconto>0</sconto>
                    <przVenditaNetto>{price_net}</przVenditaNetto>
                    <tipoPrezzo>1</tipoPrezzo>
                    <codIva>{GNB_CONFIG['cod_iva']}</codIva>
                    <matricola></matricola>
                </righe>
            </inserimentoDocumento>
        </urn:fInserimentoDocumento>
    </soapenv:Body>
</soapenv:Envelope>'''
    
    return soap_xml


def _parse_soap_response(response):
    """
    BeeStore SOAP 응답 파싱
    
    Args:
        response: requests.Response 객체
        
    Returns:
        Tuple: (success, document_id, error_msg)
               - success: bool 성공 여부
               - document_id: str 문서 ID (성공시) 또는 None
               - error_msg: str 오류 메시지 (실패시) 또는 None
    """
    
    if response.status_code != 200:
        return False, None, f"HTTP 오류: {response.status_code}"
    
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        # SOAP Fault 확인
        fault_elements = root.findall('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
        if fault_elements:
            fault_string = fault_elements[0].find('.//{http://schemas.xmlsoap.org/soap/envelope/}faultstring')
            if fault_string is not None:
                return False, None, f"SOAP Fault: {fault_string.text}"
        
        # 성공 시 문서 ID 추출
        doc_id_elements = root.findall('.//iguDocumento')
        if doc_id_elements:
            document_id = doc_id_elements[0].text
            return True, document_id, None
        else:
            return False, None, "응답에서 문서 ID를 찾을 수 없음"
            
    except Exception as e:
        return False, None, f"XML 파싱 오류: {str(e)}"


def _handle_order_failure(results, error_msg, items_info, order_id, payload_data, response_data):
    """
    주문 실패 처리
    
    Args:
        results: List 결과 리스트 (참조로 수정됨)
        error_msg: str 오류 메시지
        items_info: List 주문 항목 정보
        order_id: int 주문 ID
        payload_data: Dict 페이로드 데이터
        response_data: Dict 응답 데이터
    """
    
    # 결과 업데이트
    for result in results:
        result["success"] = False
        result["reason"] = error_msg
    
    # 📝 실패 로그
    log_order_send(
        order_id, GNB_CONFIG['retailer_name'], items_info,
        success=False, reason=error_msg, 
        payload=payload_data, response=response_data,
        error=error_msg
    )