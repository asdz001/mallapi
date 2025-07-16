import requests
import csv
from pathlib import Path

# ✅ 1. CSV URL (더블F 제공)
CSV_URL = "https://feeds.datafeedwatch.com/48802/efbb59113adce323afff7639d3516691efec6e9c.csv"

# ✅ 2. 저장 경로
EXPORT_DIR = Path("export/thedoublef")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_CSV_PATH = EXPORT_DIR / "thedoublef_flattened.csv"

# ✅ 3. CSV 수집 및 셀 분리 함수
def fetch_and_parse_csv(url):
    response = requests.get(url)
    response.raise_for_status()
    lines = response.text.strip().splitlines()

    # 첫 줄은 헤더
    header = [h.strip().strip("'") for h in lines[0].split("|")]
    rows = []

    for line in lines[1:]:
        cells = [c.strip().strip("'") for c in line.split("|")]
        # 길이 불일치 방지
        if len(cells) != len(header):
            print(f"⚠️ 필드 수 불일치 → 건너뜀: {cells[:5]}...")
            continue
        rows.append(cells)

    return header, rows

# ✅ 4. CSV 저장 함수
def save_to_csv(header, rows, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

# ✅ 5. 전체 실행 함수
def run():
    print("📥 CSV 수집 중...")
    header, rows = fetch_and_parse_csv(CSV_URL)

    print(f"📊 총 {len(rows)}건 처리 완료")
    print("💾 CSV 파일로 저장 중...")
    save_to_csv(header, rows, EXPORT_CSV_PATH)

    print(f"✅ 완료: {EXPORT_CSV_PATH}")

# ✅ 6. 실행 진입점
if __name__ == "__main__":
    run()
