"""
BeeStore API 엔드포인트 자동 스캔 (IT-G-01-ENDPOINT-SCAN)
다양한 엔드포인트에서 fInserimentoDocumento 함수 찾기
"""
import requests
import zeep
from zeep import Settings

def scan_beestore_endpoints():
    """다양한 엔드포인트를 자동으로 스캔하여 올바른 WSDL 찾기"""
    
    print("=== BeeStore 엔드포인트 자동 스캔 시작 ===\n")
    
    # 인증 정보
    user = "milaneseb2b"
    password = "w8Yc$K"
    igu_negozio = "179"
    
    # 시도할 엔드포인트들
    endpoints = [
        # 현재 사용중인 것
        "http://93.46.41.5:8180/milaneseb2b/soapBeestore.wsdl",
        
        # 가능한 다른 이름들
        "http://93.46.41.5:8180/milaneseb2b/soap.wsdl",
        "http://93.46.41.5:8180/milaneseb2b/webservice.wsdl",
        "http://93.46.41.5:8180/milaneseb2b/service.wsdl",
        "http://93.46.41.5:8180/milaneseb2b/beestore.wsdl",
        
        # 주문 관련 특화
        "http://93.46.41.5:8180/milaneseb2b/soapBeestoreOrder.wsdl",
        "http://93.46.41.5:8180/milaneseb2b/soapBeestoreB2B.wsdl",
        "http://93.46.41.5:8180/milaneseb2b/orderservice.wsdl",
        "http://93.46.41.5:8180/milaneseb2b/b2bservice.wsdl",
        
        # 포트 변경
        "http://93.46.41.5:8080/milaneseb2b/soapBeestore.wsdl",
        "http://93.46.41.5:9080/milaneseb2b/soapBeestore.wsdl",
        
        # 경로 변경
        "http://93.46.41.5:8180/soapBeestore.wsdl",
        "http://93.46.41.5:8180/webservice/soapBeestore.wsdl",
        "http://93.46.41.5:8180/soap/soapBeestore.wsdl"
    ]
    
    successful_endpoints = []
    
    for i, endpoint in enumerate(endpoints):
        print(f"=== {i+1}/{len(endpoints)}: {endpoint} ===")
        
        try:
            # 1. HTTP 접근 테스트
            print("  📡 HTTP 접근 테스트...")
            response = requests.get(endpoint, timeout=10)
            
            if response.status_code != 200:
                print(f"  ❌ HTTP 실패: {response.status_code}")
                continue
            
            print(f"  ✅ HTTP 성공: {len(response.content)} bytes")
            
            # 2. WSDL 내용 확인
            content = response.text
            if 'fInserimentoDocumento' not in content:
                print(f"  ❌ fInserimentoDocumento 없음")
                continue
            
            print(f"  ✅ fInserimentoDocumento 발견!")
            
            # 3. zeep 클라이언트 생성 테스트
            print("  🔧 zeep 클라이언트 생성...")
            settings = Settings(strict=False, xml_huge_tree=True)
            client = zeep.Client(endpoint, settings=settings)
            
            # 4. 함수 목록 확인
            operations = list(client.service._binding._operations.keys()) if hasattr(client.service, '_binding') else []
            print(f"  📋 인식된 함수들: {operations}")
            
            # 5. fInserimentoDocumento 직접 확인
            if hasattr(client.service, 'fInserimentoDocumento'):
                print("  🎯 fInserimentoDocumento 함수 발견!")
                
                # 6. 간단한 인증 테스트 (fDisponibilita로)
                if hasattr(client.service, 'fDisponibilita'):
                    print("  🔐 인증 테스트...")
                    auth_test = client.service.fDisponibilita(
                        articolo="2000016869262",
                        barcode="",
                        iguNegozio=igu_negozio,
                        user=user,
                        password=password
                    )
                    print(f"  ✅ 인증 성공: {auth_test}")
                
                # 성공한 엔드포인트 저장
                successful_endpoints.append({
                    'endpoint': endpoint,
                    'functions': operations,
                    'has_order_function': True
                })
                
                print(f"  🎉 성공! 이 엔드포인트 사용 가능")
                
            else:
                print(f"  ❌ fInserimentoDocumento 함수 인식 안됨")
                
                # 그래도 정보는 저장
                successful_endpoints.append({
                    'endpoint': endpoint,
                    'functions': operations,
                    'has_order_function': False
                })
            
        except requests.exceptions.RequestException as e:
            print(f"  ❌ 네트워크 오류: {e}")
        except Exception as e:
            print(f"  ❌ 기타 오류: {e}")
        
        print()  # 빈 줄
    
    # 결과 요약
    print("=== 스캔 결과 요약 ===")
    
    if not successful_endpoints:
        print("❌ 사용 가능한 엔드포인트를 찾지 못했습니다.")
        return None
    
    print(f"✅ {len(successful_endpoints)}개의 엔드포인트 발견:")
    
    best_endpoint = None
    for i, result in enumerate(successful_endpoints):
        status = "🎯 주문 가능" if result['has_order_function'] else "⚠️ 주문 불가"
        print(f"  {i+1}. {status}")
        print(f"     URL: {result['endpoint']}")
        print(f"     함수들: {result['functions']}")
        
        if result['has_order_function'] and not best_endpoint:
            best_endpoint = result
    
    if best_endpoint:
        print(f"\n🎉 최적 엔드포인트: {best_endpoint['endpoint']}")
        return best_endpoint
    else:
        print(f"\n⚠️ 주문 함수가 있는 엔드포인트는 없지만, 다른 옵션들이 있습니다.")
        return successful_endpoints[0] if successful_endpoints else None


if __name__ == "__main__":
    result = scan_beestore_endpoints()