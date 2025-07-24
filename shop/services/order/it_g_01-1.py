import os
import json
import requests
from lxml import etree
from datetime import datetime
from decimal import Decimal
from shop.models import Order, OrderItem

# ✅ GNB API 접속 정보 - BeeStore SOAP 서비스 연결을 위한 인증 정보
SOAP_ENDPOINT = "http://93.46.41.5:8180/milaneseb2b/soapBeestore.php"  # SOAP 서비스 엔드포인트
SOAP_USER = "milaneseb2b"  # SOAP 인증 사용자명
SOAP_PSW = "w8Yc$K"  # SOAP 인증 비밀번호
SOAP_IGUNEGOZIO = "179"  # 상점 ID
SOAP_IGUCLIENTE = "13/4/3/6867/242476/0"  # 고객 ID (성공 확인된 포맷)
SOAP_CODIVA = "NI08"  # 세금 코드

# ✅ 요청 및 응답 로그 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR_RES = "soap_responses"  # 응답 로그 저장 디렉토리
os.makedirs(LOG_DIR_RES, exist_ok=True)  # 디렉토리가 없으면 생성

def send_order(order: Order):
    """
    GNB(지앤비) 거래처로 SOAP 주문을 전송하는 함수
    
    Args:
        order: Django Order 객체 - 전송할 주문 정보
        
    Returns:
        list: 각 주문 항목별 전송 결과 리스트
              [{"sku": "상품코드", "item_id": 항목ID, "success": True/False, "reason": "메시지"}]
    """

    # ✅ 로그 저장용 디렉토리 설정 및 타임스탬프 생성
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")  # 현재 시간을 문자열로 변환
    log_file_path = os.path.join(LOG_DIR_RES, "gnb_order_log.json")  # 로그 파일 경로

    # ✅ SOAP Envelope 구성용 네임스페이스 정의
    NS_SOAPENV = "http://schemas.xmlsoap.org/soap/envelope/"  # SOAP 표준 네임스페이스
    NS_URN = "urn:wsBeestore"  # BeeStore 서비스 네임스페이스
    nsmap = {"soapenv": NS_SOAPENV, "urn": NS_URN}  # 네임스페이스 맵핑

    # ✅ SOAP Envelope 및 Body 생성
    envelope = etree.Element(etree.QName(NS_SOAPENV, "Envelope"), nsmap=nsmap)
    body = etree.SubElement(envelope, etree.QName(NS_SOAPENV, "Body"))

    # ✅ fInserimentoDocumento 메서드 호출 - BeeStore의 문서 삽입 메서드
    method = etree.SubElement(body, etree.QName(NS_URN, "fInserimentoDocumento"))
    etree.SubElement(method, "user").text = SOAP_USER  # 사용자 인증
    etree.SubElement(method, "password").text = SOAP_PSW  # 비밀번호 인증
    inserimento = etree.SubElement(method, "inserimentoDocumento")  # 문서 삽입 데이터

    # ✅ testata(헤더) 구성 - 주문 기본 정보
    testata = etree.SubElement(inserimento, "testata")
    etree.SubElement(testata, "iguNegozio").text = SOAP_IGUNEGOZIO  # 상점 ID
    etree.SubElement(testata, "iguNegozioDest").text = ""  # 목적지 상점 (비어있음)
    etree.SubElement(testata, "dtRif").text = order.created_at.strftime("%Y-%m-%d")  # 주문 생성 날짜

    # ✅ 주문번호 설정: 첫번째 상품의 external_order_number 사용
    numrif = "-"  # 기본값
    for item in order.items.all():
        if hasattr(item, "external_order_number") and item.external_order_number:
            numrif = item.external_order_number
            break
    etree.SubElement(testata, "numRif").text = numrif  # 참조 번호

    # ✅ 문서 타입 및 고객 정보 설정
    etree.SubElement(testata, "iguTipoDocumento").text = "B2BORD"  # B2B 주문 타입
    etree.SubElement(testata, "iguCliente").text = SOAP_IGUCLIENTE  # 고객 ID
    etree.SubElement(testata, "tessera").text = ""  # 멤버십 카드 (비어있음)
    
    # ✅ 고객 주소 정보 - 하드코딩된 배송지 정보
    etree.SubElement(testata, "nominativo").text = "MILANESE"  # 고객명
    etree.SubElement(testata, "indirizzo").text = "JOJUNGDAE-RO F1025, 45"  # 주소
    etree.SubElement(testata, "citta").text = "HANAM-SI"  # 도시
    etree.SubElement(testata, "cap").text = "12918"  # 우편번호
    etree.SubElement(testata, "provincia").text = "GYEONGGI-DO"  # 주/도
    etree.SubElement(testata, "telefono").text = "01073360902"  # 전화번호
    etree.SubElement(testata, "codiceStato").text = "KOR"  # 국가 코드
    etree.SubElement(testata, "partitaIva").text = "6178605369"  # 부가세 번호
    etree.SubElement(testata, "codFisc").text = "6178605369"  # 세무 번호

    # ✅ 상품 정보 생성 - 단일 상품만 처리 (BeeStore API 제한사항)
    first_item = order.items.first()  # 첫 번째 주문 항목만 처리
    if first_item:
        try:
            # ✅ righe 요소 생성 (build_test_order_fixed.py와 동일한 구조)
            righe = etree.SubElement(inserimento, "righe")  # 소문자 "righe" 사용
            
            # ✅ 상품 상세 정보 설정
            etree.SubElement(righe, "codArticolo").text = first_item.option.external_option_id  # 상품 코드
            etree.SubElement(righe, "quantitaMov").text = str(first_item.quantity)  # 수량
            etree.SubElement(righe, "przVenditaLordo").text = str(first_item.product.price_retail or Decimal("0.0"))  # 정가
            etree.SubElement(righe, "sconto").text = "0"  # 할인 (기본값 0)
            etree.SubElement(righe, "przVenditaNetto").text = str(first_item.option.price or Decimal("0.0"))  # 판매가
            etree.SubElement(righe, "tipoPrezzo").text = "1"  # 가격 타입
            etree.SubElement(righe, "codIva").text = SOAP_CODIVA  # 세금 코드
            etree.SubElement(righe, "matricola").text = ""  # 시리얼 번호 (비어있음)
            
        except Exception as e:
            print(f"❌ 상품 라인 오류: {first_item.id} → {e}")

    # ✅ SOAP XML 문자열로 변환
    xml_data = etree.tostring(envelope, pretty_print=True, encoding="utf-8", xml_declaration=True)

    # ✅ HTTP 전송 헤더 설정
    headers = {"Content-Type": "text/xml; charset=utf-8"}
    
    # ✅ 로그 저장용 디버그 정보 구성
    debug = {
        "order_id": order.id,  # 주문 ID
        "timestamp": now_str,  # 전송 시간
        "request_xml": xml_data.decode("utf-8"),  # 전송된 XML 데이터
        "order_data": {  # 주문 상세 데이터 추가
            "created_at": order.created_at.isoformat(),
            "total_items": order.items.count(),
            "processed_item": {
                "item_id": first_item.id if first_item else None,
                "external_option_id": first_item.option.external_option_id if first_item else None,
                "quantity": first_item.quantity if first_item else None,
                "price_retail": str(first_item.product.price_retail) if first_item and first_item.product.price_retail else None,
                "option_price": str(first_item.option.price) if first_item and first_item.option.price else None,
                "external_order_number": getattr(first_item, 'external_order_number', None) if first_item else None
            } if first_item else None
        },
        "soap_config": {  # SOAP 설정 정보
            "endpoint": SOAP_ENDPOINT,
            "user": SOAP_USER,
            "igu_negozio": SOAP_IGUNEGOZIO,
            "igu_cliente": SOAP_IGUCLIENTE,
            "cod_iva": SOAP_CODIVA
        }
    }

    try:
        # ✅ SOAP 요청 전송
        print(f"🚀 주문 전송 시작: Order ID {order.id}")
        response = requests.post(SOAP_ENDPOINT, data=xml_data, headers=headers, timeout=30)
        
        # ✅ 응답 기본 정보 저장
        debug["http_status"] = response.status_code
        debug["raw_response"] = response.text
        debug["response_headers"] = dict(response.headers)
        
        # ✅ XML 응답 파싱 및 분석
        try:
            tree = etree.fromstring(response.content)
            # SOAP 응답에서 주요 정보 추출
            debug["faultstring"] = tree.xpath("//faultstring/text()") or []
            debug["esito"] = tree.xpath("//esito/text()") or []
            debug["descrizione"] = tree.xpath("//descrizione/text()") or []
            debug["iguDocumento"] = tree.xpath("//iguDocumento/text()") or []
            debug["success"] = "true" in (debug["esito"][0] if debug["esito"] else "")
            
            # 성공 시 문서 ID 확인
            if debug["iguDocumento"]:
                debug["success"] = True
                debug["document_id"] = debug["iguDocumento"][0]
        except Exception as parse_error:
            debug["xml_parse_error"] = str(parse_error)
            debug["success"] = False

        # ✅ 상태코드 기반 메시지 지정
        if debug["success"]:
            order_status = "SENT"
            order_msg = f"주문 전송 성공 (문서 ID: {debug.get('document_id', 'N/A')})"
        elif response.status_code == 403:
            order_status = "FAILED"
            order_msg = "인증 오류 또는 접근 제한 (403 Forbidden)"
        elif response.status_code == 404:
            order_status = "FAILED"
            order_msg = "API 엔드포인트 오류 (404 Not Found)"
        elif response.status_code == 500 and debug.get("faultstring"):
            order_status = "FAILED"
            order_msg = f"서버 오류: {debug['faultstring'][0]}"
        else:
            order_status = "FAILED"
            order_msg = f"기타 오류 ({response.status_code})"

        # ✅ 결과를 주문 및 항목에 기록
        order.status = order_status
        order.memo = f"[GNB {order_status}] {order_msg}"
        order.save()

        # ✅ 각 주문 상품(orderitem)별 상태 저장
        for item in order.items.all():
            item.order_status = order_status
            item.order_message = order_msg
            item.save()

        print(f"✅ 주문 처리 완료: {order_status} - {order_msg}")

    except Exception as e:
        # ✅ 예외 발생 시 처리
        print(f"❌ 주문 전송 예외 발생: {e}")
        debug["success"] = False
        debug["error"] = str(e)
        debug["error_type"] = type(e).__name__
        
        # 주문 상태를 실패로 업데이트
        order.status = "FAILED"
        order.memo = f"[GNB 예외 오류] {e}"
        order.save()
        
        # 모든 주문 항목 상태 업데이트
        for item in order.items.all():
            item.order_status = "FAILED"
            item.order_message = str(e)
            item.save()

    # ✅ 누적 JSON 로그 저장 - 기존 로그에 새 로그 추가
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                all_logs = json.load(f)
        except json.JSONDecodeError:
            # 파일이 손상된 경우 새로 시작
            all_logs = []
    else:
        all_logs = []

    # 새 로그 추가
    all_logs.append(debug)

    # 로그 파일 저장
    with open(log_file_path, "w", encoding="utf-8") as f:
        json.dump(all_logs, f, indent=2, ensure_ascii=False)

    print(f"📋 로그 저장 완료: {log_file_path}")

    # ✅ 함수 반환값 - 각 주문 항목별 처리 결과
    return [
        {
            "sku": item.option.external_option_id,  # 상품 코드
            "item_id": item.id,  # 주문 항목 ID
            "success": item.order_status == "SENT",  # 성공 여부
            "reason": item.order_message  # 결과 메시지
        }
        for item in order.items.all()
    ]