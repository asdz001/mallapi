import requests
import zipfile
import io
import json

def fetch_latti_products():
    url = "http://lab.modacheva.com/json/json/demo/stock.zip"
    print("[INFO] 라띠 ZIP 파일 다운로드 시작...")

    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"[ERROR] ZIP 파일 다운로드 실패: {e}")
        return []

    print("[INFO] ZIP 파일 다운로드 완료. 압축 해제 중...")

    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            for file_name in z.namelist():
                if file_name.endswith(".json"):
                    with z.open(file_name) as f:
                        data = json.load(f)
                        print(f"[INFO] 상품 개수: {len(data['Dettagli'])}")
                        return data.get("Dettagli", [])
    except Exception as e:
        print(f"[ERROR] 압축 해제 또는 JSON 파싱 실패: {e}")
        return []

    return []
