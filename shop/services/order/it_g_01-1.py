import os
import json
import requests
from lxml import etree
from datetime import datetime
from decimal import Decimal
from shop.models import Order, OrderItem

# ✅ GNB API 접속 정보
SOAP_ENDPOINT = "http://93.46.41.5:8180/milaneseb2b/soapBeestore.php"
SOAP_USER = "milaneseb2b"
SOAP_PSW = "w8Yc$K"
SOAP_IGUNEGOZIO = "179"
SOAP_IGUCLIENTE = "13\\4\\3\\6867\\242476\\0"
SOAP_CODIVA = "NI08"

# ✅ 요청 및 응답 로그 디렉토리
LOG_DIR_REQ = "soap_requests"
LOG_DIR_RES = "soap_responses"
os.makedirs(LOG_DIR_REQ, exist_ok=True)
os.makedirs(LOG_DIR_RES, exist_ok=True)

def send_order_to_gnb(order: Order):
    """
    GNB(지앤비) 거래처로 SOAP 주문을 전송하는 함수
    :param order: Django Order 객체
    :return: True (성공) / False (실패)
    """
    # ✅ 타임스탬프와 로그 파일 경로 생성    
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    req_path = os.path.join(LOG_DIR_REQ, f"gnb_order_req_{order.id}_{now_str}.xml")
    res_path = os.path.join(LOG_DIR_RES, f"gnb_order_res_{order.id}_{now_str}.xml")
    log_file_path = os.path.join(LOG_DIR_RES, "gnb_order_log.json")

    # ✅ SOAP Envelope 구성용 네임스페이스 정의
    NS_SOAPENV = "http://schemas.xmlsoap.org/soap/envelope/"
    NS_URN = "urn:wsBeestore"
    nsmap = {"soapenv": NS_SOAPENV, "urn": NS_URN}

    # ✅ SOAP Envelope 및 Body 생성
    envelope = etree.Element(etree.QName(NS_SOAPENV, "Envelope"), nsmap=nsmap)
    body = etree.SubElement(envelope, etree.QName(NS_SOAPENV, "Body"))

    # ✅ fInserimentoDocumento 메서드 호출        
    method = etree.SubElement(body, etree.QName(NS_URN, "fInserimentoDocumento"))
    etree.SubElement(method, "user").text = SOAP_USER
    etree.SubElement(method, "password").text = SOAP_PSW
    inserimento = etree.SubElement(method, "inserimentoDocumento")

    # ✅ testata (주문 헤더 정보 구성)
    testata = etree.SubElement(inserimento, "testata")
    etree.SubElement(testata, "iguNegozio").text = SOAP_IGUNEGOZIO
    etree.SubElement(testata, "iguNegozioDest").text = ""
    etree.SubElement(testata, "dtRif").text = order.created_at.strftime("%Y-%m-%d")
    etree.SubElement(testata, "numRif").text = order.external_order_number  # 외부주문번호 사용
    etree.SubElement(testata, "iguTipoDocumento").text = "B2BORD"
    etree.SubElement(testata, "iguCliente").text = SOAP_IGUCLIENTE
    etree.SubElement(testata, "tessera").text = ""
    etree.SubElement(testata, "nominativo").text = "MILANESE"
    etree.SubElement(testata, "indirizzo").text = "JOJUNGDAE-RO F1025, 45"
    etree.SubElement(testata, "citta").text = order.city or "HANAM-SI"
    etree.SubElement(testata, "cap").text = order.zipcode or "12918"
    etree.SubElement(testata, "provincia").text = order.state or "GYEONGGI-DO"
    etree.SubElement(testata, "telefono").text = order.phone or "01073360902"
    etree.SubElement(testata, "codiceStato").text = "KOR"
    etree.SubElement(testata, "partitaIva").text = "6178605369"
    etree.SubElement(testata, "codFisc").text = "6178605369"

    # ✅ Rows (주문 상품 목록)
    rows = etree.SubElement(inserimento, "Rows")
    for item in order.items.all():
        try:
            # 🔸 상품별 가격 설정               
            riga = etree.SubElement(rows, "riga")
            etree.SubElement(riga, "codArticolo").text = item.external_option_id or item.option.external_option_id
            etree.SubElement(riga, "quantitaMov").text = str(item.quantity)
            etree.SubElement(riga, "przVenditaLordo").text = str(item.product.retail_price or Decimal("0.0"))
            etree.SubElement(riga, "przVenditaNetto").text = str(item.price or Decimal("0.0"))
            etree.SubElement(riga, "tipoPrezzo").text = "1"
            etree.SubElement(riga, "codIva").text = SOAP_CODIVA
        except Exception as e:
            print(f"❌ 상품 라인 오류: {item.id} → {e}")

    # ✅ SOAP XML 생성 및 저장
    xml_data = etree.tostring(envelope, pretty_print=True, encoding="utf-8", xml_declaration=True)
    with open(req_path, "wb") as f:
        f.write(xml_data)

    # ✅ HTTP 헤더 설정
    headers = {"Content-Type": "text/xml; charset=utf-8"}
    # ✅ 디버그 초기값 구성
    debug = {
        "order_id": order.id,
        "timestamp": now_str,
        "request_file": req_path,
        "response_file": res_path,
        "request_xml": xml_data.decode("utf-8")
    }

    try:
        # ✅ SOAP 요청 전송             
        response = requests.post(SOAP_ENDPOINT, data=xml_data, headers=headers, timeout=30)
        # ✅ 응답 결과 저장            
        with open(res_path, "wb") as f:
            f.write(response.content)
        # ✅ XML 응답 파싱
        tree = etree.fromstring(response.content)
        debug["http_status"] = response.status_code
        debug["raw_response"] = response.text
        debug["faultstring"] = tree.xpath("//faultstring/text()") or []
        debug["esito"] = tree.xpath("//esito/text()") or []
        debug["descrizione"] = tree.xpath("//descrizione/text()") or []
        debug["success"] = "true" in (debug["esito"][0] if debug["esito"] else "")

        # ✅ HTTP 상태코드 기반 오류 메시지 지정
        if debug["success"]:
            order_status = "SENT"
            order_msg = ""
        elif response.status_code == 403:
            order_status = "FAILED"
            order_msg = "인증 오류 또는 접근 제한 (403 Forbidden)"
        elif response.status_code == 404:
            order_status = "FAILED"
            order_msg = "API 엔드포인트 오류 (404 Not Found)"
        elif response.status_code == 500 and debug["faultstring"]:
            order_status = "FAILED"
            order_msg = f"서버 오류: {debug['faultstring'][0]}"
        else:
            order_status = "FAILED"
            order_msg = f"기타 오류 ({response.status_code})"

        # ✅ 주문 객체 저장
        order.status = order_status
        order.memo = f"[GNB {order_status}] {order_msg}"
        order.save()

        # ✅ 각 주문 상품(orderitem)별 상태 저장
        for item in order.items.all():
            item.order_status = order_status
            item.order_message = order_msg
            item.save()

    except Exception as e:
        # ✅ 예외 발생 시 오류 기록         
        debug["success"] = False
        debug["error"] = str(e)
        order.status = "FAILED"
        order.memo = f"[GNB 예외 오류] {e}"
        order.save()
        for item in order.items.all():
            item.order_status = "FAILED"
            item.order_message = str(e)
            item.save()

    # ✅ JSON 로그 누적 저장 방식으로 변경
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                all_logs = json.load(f)
        except json.JSONDecodeError:
            all_logs = []
    else:
        all_logs = []

    all_logs.append(debug)

    with open(log_file_path, "w", encoding="utf-8") as f:
        json.dump(all_logs, f, indent=2, ensure_ascii=False)

    return debug["success"]
