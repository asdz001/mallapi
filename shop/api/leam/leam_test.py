import requests
import os
from PIL import Image
from io import BytesIO

# ✅ 수정된 이미지 API 경로
IMAGE_BASE_URL = "https://srv2.best-fashion.net/ApiV3/img"
TEST_IMAGE_NAME = "NDcwNTkw.JPG"  # 테스트용 이미지 이름 (존재하는 파일로 교체 필요)

# 저장 경로
SAVE_DIR = "media/leam_test"
os.makedirs(SAVE_DIR, exist_ok=True)

def download_image(image_name: str):
    url = f"{IMAGE_BASE_URL}/{image_name}"
    save_path = os.path.join(SAVE_DIR, image_name)

    try:
        print(f"📥 다운로드 시도: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        image = Image.open(BytesIO(response.content))
        image.save(save_path)
        print(f"✅ 이미지 저장 완료: {save_path}")

    except requests.HTTPError as e:
        print(f"❌ HTTP 오류: {e}")
    except Exception as e:
        print(f"❌ 이미지 저장 실패: {e}")

if __name__ == "__main__":
    download_image(TEST_IMAGE_NAME)
