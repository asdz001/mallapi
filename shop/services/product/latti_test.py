import requests
import zipfile
import io
import json
import pandas as pd
import os

# 바탕화면 경로
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
save_path = os.path.join(desktop_path, "라띠 전체 데이터.xlsx")

# 운영용 라띠 ZIP URL
LATTIZIP_URL = "https://lab.modacheva.com/json/json/milanese/stock.zip"

def save_all_latti_data_to_excel():
    print("📥 라띠 운영용 stock.zip 다운로드 중...")
    response = requests.get(LATTIZIP_URL)

    if response.status_code != 200:
        print("❌ 다운로드 실패")
        return

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        filename = zf.namelist()[0]
        with zf.open(filename) as raw_file:
            # ✅ 인코딩 명시하여 수동 디코딩
            content = raw_file.read().decode("latin-1")  # 또는 "ISO-8859-1"
            data = json.loads(content)

    items = data.get("Dettagli", [])
    print(f"✅ 총 {len(items)}개 상품 로드 완료")

    df = pd.DataFrame(items)
    df.to_excel(save_path, index=False)

    print(f"📄 엑셀 저장 완료: {save_path}")

# 실행
if __name__ == "__main__":
    save_all_latti_data_to_excel()
