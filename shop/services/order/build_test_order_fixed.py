import os
from lxml import etree
import requests
from datetime import datetime
import json

# ✅ SOAP 접속 정보
SOAP_ENDPOINT = "http://93.46.41.5:8180/milaneseb2b/soapBeestore.php"
SOAP_USER = "milaneseb2b"
SOAP_PSW = "w8Yc$K"
SOAP_IGUNEGOZIO = "179"
SOAP_IGUCLIENTE = "13\\4\\3\\6867\\242476\\0"  # 성공한 포맷
SOAP_CODIVA = "NI08"

LOG_DIR_REQ = "soap_requests"
LOG_DIR_RES = "soap_responses"
os.makedirs(LOG_DIR_REQ, exist_ok=True)
os.makedirs(LOG_DIR_RES, exist_ok=True)

def send_test_order():
    """
    성공 확인된 포맷으로 실제 주문 전송
    """
    NS_SOAPENV = "http://schemas.xmlsoap.org/soap/envelope/"
    NS_URN = "urn:wsBeestore"
    nsmap = {"soapenv": NS_SOAPENV, "urn": NS_URN}

    envelope = etree.Element(etree.QName(NS_SOAPENV, "Envelope"), nsmap=nsmap)
    body = etree.SubElement(envelope, etree.QName(NS_SOAPENV, "Body"))
    method = etree.SubElement(body, etree.QName(NS_URN, "fInserimentoDocumento"))

    etree.SubElement(method, "user").text = SOAP_USER
    etree.SubElement(method, "password").text = SOAP_PSW

    inserimento = etree.SubElement(method, "inserimentoDocumento")

    # testata
    testata = etree.SubElement(inserimento, "testata")
    etree.SubElement(testata, "iguNegozio").text = SOAP_IGUNEGOZIO
    etree.SubElement(testata, "iguNegozioDest").text = ""
    etree.SubElement(testata, "dtRif").text = datetime.now().strftime("%Y-%m-%d")
    etree.SubElement(testata, "numRif").text = f"20250703-ORDER-172-172-G01"
    etree.SubElement(testata, "iguTipoDocumento").text = "B2BORD"
    etree.SubElement(testata, "iguCliente").text = SOAP_IGUCLIENTE
    etree.SubElement(testata, "tessera").text = ""
    etree.SubElement(testata, "nominativo").text = "MILANESE"
    etree.SubElement(testata, "indirizzo").text = "JOJUNGDAE-RO F1025, 45"
    etree.SubElement(testata, "citta").text = "HANAM-SI"
    etree.SubElement(testata, "cap").text = "12918"
    etree.SubElement(testata, "provincia").text = "GYEONGGI-DO"
    etree.SubElement(testata, "telefono").text = "01073360902"
    etree.SubElement(testata, "codiceStato").text = "KOR"
    etree.SubElement(testata, "partitaIva").text = "6178605369"
    etree.SubElement(testata, "codFisc").text = "6178605369"
    etree.SubElement(testata, "note").text = "최종 실제 주문 테스트"

    # righe
    righe = etree.SubElement(inserimento, "righe")
    etree.SubElement(righe, "codArticolo").text = "2000014719293"
    etree.SubElement(righe, "quantitaMov").text = "1"
    etree.SubElement(righe, "przVenditaLordo").text = "680.00"
    etree.SubElement(righe, "sconto").text = "0"
    etree.SubElement(righe, "przVenditaNetto").text = "272.00"
    etree.SubElement(righe, "tipoPrezzo").text = "1"
    etree.SubElement(righe, "codIva").text = SOAP_CODIVA
    etree.SubElement(righe, "matricola").text = ""

    xml_data = etree.tostring(envelope, pretty_print=True, encoding="utf-8", xml_declaration=True)
    
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    req_file = os.path.join(LOG_DIR_REQ, f"final_test_{now_str}.xml")
    res_file = os.path.join(LOG_DIR_RES, f"final_test_{now_str}.xml")
    
    with open(req_file, "wb") as f:
        f.write(xml_data)
    
    print("🎯 최종 주문 테스트")
    print("=" * 80)
    print(f"📤 요청 파일: {req_file}")
    print("📋 주문 내용:")
    print("  - 상품: HIMMEL LTS SHOPPER MED P6")
    print("  - 코드: 2000014719293")
    print("  - 수량: 1")
    print("  - 가격: 680.00 (순가격: 557.38)")
    print("=" * 80)
    
    headers = {"Content-Type": "text/xml; charset=utf-8"}
    
    try:
        print("🚀 주문 전송 중...")
        response = requests.post(SOAP_ENDPOINT, data=xml_data, headers=headers, timeout=30)
        
        with open(res_file, "wb") as f:
            f.write(response.content)
        
        print(f"📥 응답 받음 (HTTP {response.status_code})")
        print("📋 전체 응답:")
        print(response.text)
        print("=" * 80)
        
        # 상세 분석
        result = analyze_response(response)
        return result
        
    except Exception as e:
        print(f"❌ 요청 오류: {e}")
        return {"success": False, "error": str(e)}

def analyze_response(response):
    """
    응답 상세 분석
    """
    result = {
        "http_status": response.status_code,
        "success": False,
        "raw_response": response.text
    }
    
    if response.status_code == 200:
        try:
            tree = etree.fromstring(response.content)
            
            # 성공 응답 확인
            igu_documento = tree.xpath("//iguDocumento/text()")
            if igu_documento:
                result["success"] = True
                result["iguDocumento"] = igu_documento[0]
                print("✅ 주문 성공!")
                print(f"🎉 생성된 문서 IGU: {igu_documento[0]}")
                print("📋 이제 실제 BeeStore 시스템에 주문이 등록되었습니다!")
                return result
            
            # 오류 응답 확인
            fault_code = tree.xpath("//faultcode/text()")
            fault_string = tree.xpath("//faultstring/text()")
            
            if fault_string:
                result["fault_code"] = fault_code[0] if fault_code else "Unknown"
                result["fault_string"] = fault_string[0]
                print(f"❌ SOAP 오류:")
                print(f"   코드: {result['fault_code']}")
                print(f"   메시지: {result['fault_string']}")
                
                # 오류 해석
                if "Errore numero:2" in fault_string[0]:
                    print("💡 분석: IGUCliente를 찾을 수 없음")
                elif "Errore numero:3" in fault_string[0]:
                    print("💡 분석: Tessera를 찾을 수 없음")
                elif "Impostare almeno una riga" in fault_string[0]:
                    print("💡 분석: 문서 행이 누락됨 (XML 구조 문제)")
                else:
                    print("💡 분석: 기타 서버 오류")
                    
        except Exception as parse_error:
            print(f"❌ 응답 파싱 오류: {parse_error}")
            result["parse_error"] = str(parse_error)
    else:
        print(f"❌ HTTP 오류: {response.status_code}")
    
    return result

def check_order_status(igu_documento):
    """
    생성된 주문의 상태 확인 (선택사항)
    """
    # 추후 fStatoPrenotazioni 함수 구현 시 사용
    print(f"📋 주문 상태 확인 기능 (IGU: {igu_documento})")
    print("💡 fStatoPrenotazioni 함수로 구현 예정")

def main():
    """
    최종 검증 실행
    """
    print("🔬 BeeStore 주문 성공 최종 검증")
    print("=" * 80)
    print("목표: 실제 상품 주문이 BeeStore에 성공적으로 등록되는지 확인")
    print("=" * 80)
    
    result = send_test_order()
    
    print("\n" + "=" * 80)
    print("📊 최종 결과:")
    
    if result.get("success", False):
        print("🎉 성공! BeeStore B2B 주문 시스템이 완전히 작동합니다!")
        print(f"📄 생성된 문서: {result.get('iguDocumento', 'N/A')}")
        print("\n✅ 이제 다음 단계를 진행할 수 있습니다:")
        print("  1. Django/FastAPI와 연동")
        print("  2. 실제 쇼핑몰에서 주문 전송")
        print("  3. 주문 상태 추적 시스템 구축")
        print("  4. 재고 관리 시스템 구축")
        
        # 주문 상태 확인 (옵션)
        if input("\n주문 상태를 확인하시겠습니까? (y/n): ").lower() == 'y':
            check_order_status(result.get('iguDocumento'))
            
    else:
        print("❌ 아직 문제가 남아있습니다.")
        print("🔍 확인 필요 사항:")
        
        if "fault_string" in result:
            fault = result["fault_string"]
            if "Errore numero:2" in fault:
                print("  - IGUCliente 값이 여전히 잘못됨")
                print("  - BeeStore 관리자에게 올바른 고객 ID 확인 필요")
            elif "Impostare almeno una riga" in fault:
                print("  - XML 구조 문제 (righe 부분)")
                print("  - WSDL 정의와 실제 구현 차이 가능성")
            else:
                print(f"  - 기타 오류: {fault}")
        else:
            print("  - 네트워크 또는 서버 연결 문제")
    
    print("=" * 80)
    return result

if __name__ == "__main__":
    main()