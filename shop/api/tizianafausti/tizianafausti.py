import sys
import os
import django
import time
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ✅ Django 설정 (DB 접근 가능하게)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mallapi.settings")
    

def run_tiziana_login_and_crawl():
    options = Options()
    # options.add_argument("--headless")  # 개발 중일 땐 주석 처리
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    try:
        print("🚪 로그인 페이지 접속 중...")
        driver.get("https://www.tizianafausti.net/vip2_en/customer/account/login/")
        driver.refresh()

        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "form_key"))
        )

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        driver.find_element(By.ID, "email").send_keys("md@milanese.co.kr")
        driver.find_element(By.ID, "pass").send_keys("milanese11!!")
        driver.find_element(By.CSS_SELECTOR, "button.login").click()
        time.sleep(3)

        print("🛍️ DESIGNERS 메뉴 클릭 중...")
        designers_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "DESIGNERS"))
        )
        designers_link.click()

        print("📄 상품 리스트 로딩 대기 중...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".product-item-link"))
        )

        product_elements = driver.find_elements(By.CSS_SELECTOR, ".product-item-link")
        print(f"✅ 상품 {len(product_elements)}개 수집됨")

        # 상품 이름들 출력
        for i, elem in enumerate(product_elements[:10], start=1):  # 처음 10개만 예시
            print(f"{i}. {elem.text.strip()}")

    except Exception as e:
        print("❌ 예외 발생:")
        traceback.print_exc()

    finally:
        driver.quit()

if __name__ == "__main__":
    print("📦 티지아나 상품 크롤링 시작")
    run_tiziana_login_and_crawl()
    print("✅ 작업 완료")
