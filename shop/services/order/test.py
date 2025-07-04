
from zeep import Client
from zeep.helpers import serialize_object

# 로컬에 있는 WSDL 파일 경로
wsdl_path = "file:///C:/Users/USER/myproject/mallapi/soapBeestore.wsdl"  # ← 윈도우라면 file:///C:/...

client = Client(wsdl=wsdl_path)

binding = client.wsdl.bindings["{urn:wsBeestore}fInserimentoDocumentoBinding"]
operation = binding.get("fInserimentoDocumento")
print("\n🔍 fInserimentoDocumento 구조:")
print(operation.input.body.type)