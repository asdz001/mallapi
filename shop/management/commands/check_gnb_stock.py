from django.core.management.base import BaseCommand
import requests
from lxml import etree

class Command(BaseCommand):
    help = "GNB(지앤비) 재고 조회용 SOAP API 호출 테스트"

    def add_arguments(self, parser):
        parser.add_argument('--sku', type=str, help='CodiceArticolo (SKU)')

    def handle(self, *args, **options):
        sku = options.get("sku")
        if not sku:
            self.stderr.write("❌ SKU (--sku 값)이 필요합니다.")
            return

        # 인증 정보 및 설정값
        SOAP_ENDPOINT = "http://93.46.41.5:8180/milaneseb2b/soapBeestore.php"
        SOAP_USER = "milaneseb2b"
        SOAP_PSW = "w8Yc$K"
        SOAP_IGUNEGOZIO = "179"
        SOAP_IGUCLIENTE = "13/4/3/6867/242476/0"

        # 네임스페이스 선언
        NS_SOAPENV = "http://schemas.xmlsoap.org/soap/envelope/"
        NS_URN = "urn:wsBeestore"

        # Envelope 생성
        envelope = etree.Element(etree.QName(NS_SOAPENV, "Envelope"), nsmap={"soapenv": NS_SOAPENV, "urn": NS_URN})
        body = etree.SubElement(envelope, etree.QName(NS_SOAPENV, "Body"))
        method = etree.SubElement(body, etree.QName(NS_URN, "fDisponibilita"))

        # 필수 인자 5개 추가 (순서 중요하지 않지만 누락되면 오류)
        etree.SubElement(method, "CodiceArticolo").text = sku
        etree.SubElement(method, "IGUNegozio").text = SOAP_IGUNEGOZIO
        etree.SubElement(method, "User").text = SOAP_USER
        etree.SubElement(method, "Password").text = SOAP_PSW
        etree.SubElement(method, "IGUCliente").text = SOAP_IGUCLIENTE

        # XML 문자열로 변환
        xml_str = etree.tostring(envelope, pretty_print=True, encoding="utf-8", xml_declaration=True)
        headers = {"Content-Type": "text/xml; charset=utf-8"}

        self.stdout.write(f"\n🚀 GNB 재고조회 API 호출 중 (SKU: {sku})...")

        try:
            response = requests.post(SOAP_ENDPOINT, data=xml_str, headers=headers, timeout=30)
        except requests.RequestException as e:
            self.stderr.write(f"❌ 요청 실패: {e}")
            return

        self.stdout.write(f"🔁 HTTP 상태코드: {response.status_code}")
        self.stdout.write("📄 원시 응답 XML:")
        self.stdout.write(response.text)

        try:
            tree = etree.fromstring(response.content)
            disponibilita = tree.xpath("//Disponibilita/text()")
            if disponibilita:
                self.stdout.write(f"✅ 재고 수량: {disponibilita[0]}")
            else:
                self.stdout.write("⚠️ 'Disponibilita' 응답 없음. SKU가 존재하지 않거나 권한 없음.")
        except Exception as e:
            self.stderr.write(f"❌ XML 파싱 오류: {e}")