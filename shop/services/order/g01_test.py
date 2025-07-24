"""
BeeStore API 연결 테스트 (IT-G-01)
단계별 누적 테스트 방식 - 7단계: 직접 XML SOAP 요청 = 테스트용 완성본 샘플
"""
import requests
import zeep
from datetime import datetime
from decimal import Decimal
import xml.etree.ElementTree as ET

def test_beestore_step1_2_3_4_5_6_7_xml():
    """1+2+3+4+5+6+7단계: 설정값 + WSDL 접근 + SOAP 클라이언트 + API 함수 호출 + 주문 헤더 + 상품 목록 + 직접 XML 주문 전송"""
    print("=== 1단계: 설정값 검증 ===")
    
    # BeeStore 연결 정보
    wsdl_url = "http://93.46.41.5:8180/milaneseb2b/soapBeestore.wsdl"
    soap_endpoint = "http://93.46.41.5:8180/milaneseb2b/soapBeestore.php"  # 실제 SOAP 엔드포인트
    user = "milaneseb2b"
    password = "w8Yc$K"
    igu_negozio = "179"
    #igu_cliente = "13/4/3/6867/242476/0"
    igu_cliente ="13\\4\\3\\6867\\242476\\0"
    cod_iva = "NI08"
    
    print(f"WSDL URL: {wsdl_url}")
    print(f"SOAP Endpoint: {soap_endpoint}")
    print(f"User: {user}")
    print(f"IGU Negozio: {igu_negozio}")
    print(f"IGU Cliente: {igu_cliente}")
    print(f"Cod IVA: {cod_iva}")
    
    print("✓ 1단계 완료: 설정값 확인됨")
    
    print("\n=== 2단계: WSDL 접근 체크 ===")
    
    try:
        response = requests.get(wsdl_url, timeout=10)
        print(f"WSDL 응답 코드: {response.status_code}")
        print(f"응답 크기: {len(response.content)} bytes")
        
        if response.status_code == 200:
            print("✓ 2단계 완료: WSDL 접근 성공")
        else:
            print("✗ 2단계 실패: WSDL 접근 불가")
            return False
            
    except Exception as e:
        print(f"✗ 2단계 실패: {str(e)}")
        return False
    
    print("\n=== 3단계: SOAP 클라이언트 생성 ===")
    
    try:
        from zeep import Settings
        settings = Settings(strict=False, xml_huge_tree=True)
        client = zeep.Client(wsdl_url, settings=settings)
        print("✓ SOAP 클라이언트 생성 성공")
        print("✓ 3단계 완료: SOAP 클라이언트 준비됨")
        
    except Exception as e:
        print(f"✗ 3단계 실패: {str(e)}")
        return False
    
    print("\n=== 4단계: API 함수 호출 테스트 ===")
    
    try:
        print("fDisponibilita 함수 호출 시도...")
        
        response = client.service.fDisponibilita(
            articolo="2000016869262",
            barcode="",
            iguNegozio=igu_negozio,
            user=user,
            password=password
        )
        
        print(f"API 응답: {response}")
        print("✓ 4단계 완료: API 함수 호출 성공")
        
    except Exception as e:
        print(f"✗ 4단계 실패: {str(e)}")
        return False
    
    print("\n=== 5단계: 주문 헤더 구조 생성 ===")
    
    try:
        test_order_data = {
            'order_id': 334,
            'created_at': datetime.now(),
            'item_id': 334
        }
        
        header = {
            'iguNegozio': igu_negozio,
            'dtRif': test_order_data['created_at'].strftime('%Y-%m-%d'),
            'numRif': test_order_data['item_id'],
            'iguTipoDocumento': 'B2BORD',
            'iguCliente': igu_cliente,
            'nominativo': 'MILANESE',
            'indirizzo': 'JOJUNGDAE-RO F1025, 45',
            'citta': 'HANAM-SI',
            'cap': '12918',
            'provincia': 'GYEONGGI-DO',
            'telefono': '01073360902',
            'codiceStato': 'KOR',
            'partitaIva': '6178605369',
            'codFisc': '6178605369'
        }
        
        print("주문 헤더 구조:")
        for key, value in header.items():
            print(f"  {key}: {value}")
        
        print("✓ 5단계 완료: 주문 헤더 구조 생성됨")
        
    except Exception as e:
        print(f"✗ 5단계 실패: {str(e)}")
        return False
    
    print("\n=== 6단계: 상품 목록 구조 생성 ===")
    
    try:
        test_items = [
            {
                'item_id': 334,
                'external_option_id': '2000016869262',
                'quantity': 2,
                'price_retail': Decimal('100.00'),
                'option_price': Decimal('90.00')
            }
        ]
        
        details = []
        for item in test_items:
            detail = {
                'codArticolo': item['external_option_id'],
                'quantitaMov': item['quantity'],
                'przVenditaLordo': float(item['price_retail']),
                'sconto': 0,
                'przVenditaNetto': float(item['option_price']),
                'tipoPrezzo': 1,
                'codIva': cod_iva,
                'matricola': ''
            }
            details.append(detail)
        
        print("상품 목록 구조:")
        for i, detail in enumerate(details):
            print(f"  상품 {i+1}:")
            for key, value in detail.items():
                print(f"    {key}: {value}")
        
        print("✓ 6단계 완료: 상품 목록 구조 생성됨")
        
    except Exception as e:
        print(f"✗ 6단계 실패: {str(e)}")
        return False
    
    print("\n=== 7단계: 직접 XML SOAP 주문 전송 ===")
    
    try:
        print("📋 XML SOAP 요청 생성 중...")
        
        # SOAP XML 생성 (이전 파일 구조 참고)
        soap_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:wsBeestore">
    <soapenv:Body>
        <urn:fInserimentoDocumento>
            <user>{user}</user>
            <password>{password}</password>
            <inserimentoDocumento>
                <testata>
                    <iguNegozio>{header['iguNegozio']}</iguNegozio>
                    <iguNegozioDest></iguNegozioDest>
                    <dtRif>{header['dtRif']}</dtRif>
                    <numRif>{header['numRif']}</numRif>
                    <iguTipoDocumento>{header['iguTipoDocumento']}</iguTipoDocumento>
                    <iguCliente>{header['iguCliente']}</iguCliente>
                    <tessera></tessera>
                    <nominativo>{header['nominativo']}</nominativo>
                    <indirizzo>{header['indirizzo']}</indirizzo>
                    <citta>{header['citta']}</citta>
                    <cap>{header['cap']}</cap>
                    <provincia>{header['provincia']}</provincia>
                    <telefono>{header['telefono']}</telefono>
                    <codiceStato>{header['codiceStato']}</codiceStato>
                    <partitaIva>{header['partitaIva']}</partitaIva>
                    <codFisc>{header['codFisc']}</codFisc>
                </testata>
                <righe>
                    <codArticolo>{details[0]['codArticolo']}</codArticolo>
                    <quantitaMov>{details[0]['quantitaMov']}</quantitaMov>
                    <przVenditaLordo>{details[0]['przVenditaLordo']}</przVenditaLordo>
                    <sconto>{details[0]['sconto']}</sconto>
                    <przVenditaNetto>{details[0]['przVenditaNetto']}</przVenditaNetto>
                    <tipoPrezzo>{details[0]['tipoPrezzo']}</tipoPrezzo>
                    <codIva>{details[0]['codIva']}</codIva>
                    <matricola>{details[0]['matricola']}</matricola>
                </righe>
            </inserimentoDocumento>
        </urn:fInserimentoDocumento>
    </soapenv:Body>
</soapenv:Envelope>'''
        
        print("✅ XML 생성 완료")
        print(f"XML 크기: {len(soap_xml)} 문자")
        
        # HTTP 헤더 설정
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'urn:fInserimentoDocumentoAction'
        }
        
        print(f"\n📤 SOAP 요청 전송...")
        print(f"  엔드포인트: {soap_endpoint}")
        print(f"  헤더: {headers}")
        
        # 실제 SOAP 요청 전송
        response = requests.post(
            soap_endpoint,
            data=soap_xml.encode('utf-8'),
            headers=headers,
            timeout=30
        )
        
        print(f"\n📥 응답 수신:")
        print(f"  HTTP 상태: {response.status_code}")
        print(f"  응답 크기: {len(response.content)} bytes")
        print(f"  응답 헤더: {dict(response.headers)}")
        
        # 응답 내용 분석
        if response.status_code == 200:
            print(f"\n✅ HTTP 요청 성공!")
            print(f"응답 내용:")
            print(response.text[:1000])  # 처음 1000자만 출력
            
            # XML 응답 파싱 시도
            try:
                root = ET.fromstring(response.content)
                
                # 성공/실패 확인
                fault_elements = root.findall('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
                if fault_elements:
                    print(f"❌ SOAP Fault 발생:")
                    for fault in fault_elements:
                        fault_string = fault.find('.//{http://schemas.xmlsoap.org/soap/envelope/}faultstring')
                        if fault_string is not None:
                            print(f"  오류: {fault_string.text}")
                else:
                    print(f"✅ SOAP 응답 정상 - Fault 없음")
                    
                    # 성공 응답에서 문서 ID 찾기
                    doc_id_elements = root.findall('.//iguDocumento')
                    if doc_id_elements:
                        doc_id = doc_id_elements[0].text
                        print(f"🎉 주문 생성 성공! 문서 ID: {doc_id}")
                        return doc_id
                    else:
                        print(f"⚠️ 응답은 정상이지만 문서 ID를 찾을 수 없음")
                        
            except Exception as parse_error:
                print(f"⚠️ XML 파싱 오류: {parse_error}")
                print("→ 원본 응답을 확인해주세요")
        
        else:
            print(f"❌ HTTP 요청 실패: {response.status_code}")
            print(f"응답 내용: {response.text}")
        
        print("✓ 7단계 완료: 직접 XML 주문 전송 시도됨")
        return response
        
    except Exception as e:
        print(f"❌ 7단계 실패: XML 주문 전송 오류")
        print(f"  오류 타입: {type(e).__name__}")  
        print(f"  오류 메시지: {str(e)}")
        return False


if __name__ == "__main__":
    # 1+2+3+4+5+6+7단계 테스트
    result = test_beestore_step1_2_3_4_5_6_7_xml()