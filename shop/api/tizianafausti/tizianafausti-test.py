#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
티지아나 파우스티 Selenium 기반 샘플 크롤러
목적: 5개 상품 샘플 데이터 수집 및 JSON 저장
거래처코드: IT-T-02
버전: 3.0 (Selenium 기반)
"""

import time
import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 로깅 시스템
def get_tiziana_logger():
    """티지아나 전용 로거 생성"""
    retailer_code = "IT-T-02"
    logger_name = f"product_logger_{retailer_code}"
    logger = logging.getLogger(logger_name)

    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    # 로그 디렉토리 설정
    LOG_DIR = Path("log_backups") / "product_collect"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    log_path = LOG_DIR / f"{retailer_code}.log"
    
    # 핸들러 설정
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"📝 티지아나 로거 초기화 완료: {log_path}")
    return logger

def log_session_separator(logger, label=""):
    """세션 구분자 출력"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = f"📦 {label}" if label else ""
    logger.info("")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"🕒 실행 시작: {now} {label}")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("")

class TizianaSeleniumCrawler:
    def __init__(self):
        """크롤러 초기화"""
        self.logger = get_tiziana_logger()
        log_session_separator(self.logger, "티지아나 Selenium 샘플 크롤러")
        
        # JSON 저장 경로 설정
        self.export_dir = Path("export") / "TIZIANA"
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.output_json = self.export_dir / "tiziana_sample_products.json"
        
        self.logger.info(f"📁 JSON 저장 경로: {self.output_json}")
        
        # 로그인 정보
        self.email = "md@milanese.co.kr"
        self.password = "milanese11!!"
        
        # 수집된 상품 데이터
        self.sample_products = []
        
        self.driver = None
        
        self.logger.info("🚀 Selenium 크롤러 초기화 완료")

    def setup_driver(self):
        """Chrome 드라이버 설정"""
        try:
            self.logger.info("🌐 Chrome 드라이버 설정 중...")
            
            options = Options()
            # options.add_argument("--headless")  # 개발 중에는 주석 처리
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("✅ Chrome 드라이버 설정 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 드라이버 설정 오류: {str(e)}")
            return False

    def login(self):
        """로그인 처리"""
        try:
            self.logger.info("🔐 로그인 시작...")
            
            login_url = "https://www.tizianafausti.net/vip2_en/customer/account/login/"
            self.logger.info(f"📍 로그인 페이지 접속: {login_url}")
            
            self.driver.get(login_url)
            self.driver.refresh()
            
            # 페이지 로딩 대기
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # form_key 필드 대기
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "form_key"))
            )
            
            # 이메일 입력
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_field.clear()
            email_field.send_keys(self.email)
            self.logger.info(f"👤 이메일 입력: {self.email}")
            
            # 패스워드 입력
            pass_field = self.driver.find_element(By.ID, "pass")
            pass_field.clear()
            pass_field.send_keys(self.password)
            self.logger.info("🔒 패스워드 입력 완료")
            
            # 로그인 버튼 클릭
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button.login")
            login_button.click()
            self.logger.info("🖱️ 로그인 버튼 클릭")
            
            time.sleep(3)
            
            # 로그인 성공 확인
            current_url = self.driver.current_url
            if "account" in current_url.lower():
                self.logger.info("✅ 로그인 성공!")
                return True
            else:
                self.logger.error("❌ 로그인 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 로그인 오류: {str(e)}")
            return False

    def navigate_to_products(self):
        """상품 페이지로 이동 (개선된 버전)"""
        try:
            self.logger.info("🛍️ 상품 페이지 이동 중...")
            
            # DESIGNERS 메뉴 클릭
            designers_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "DESIGNERS"))
            )
            designers_link.click()
            self.logger.info("🎨 DESIGNERS 메뉴 클릭 완료")
            
            # 페이지 로딩 대기 (더 길게)
            time.sleep(5)
            self.logger.info("⏳ 페이지 로딩 대기 중...")
            
            # 여러 셀렉터로 상품 링크 찾기 시도
            selectors_to_try = [
                ".product-item-link",
                ".product-link", 
                ".product-name a",
                ".product-item a",
                "a[href*='/vip2_en/']",
                ".item-link"
            ]
            
            product_elements = []
            for selector in selectors_to_try:
                try:
                    self.logger.info(f"🔍 셀렉터 시도: {selector}")
                    
                    # 대기 시간을 늘려서 시도
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    
                    product_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if product_elements:
                        self.logger.info(f"✅ 셀렉터 '{selector}'로 {len(product_elements)}개 상품 발견")
                        break
                    
                except TimeoutException:
                    self.logger.info(f"⚠️ 셀렉터 '{selector}' 타임아웃")
                    continue
                except Exception as e:
                    self.logger.info(f"⚠️ 셀렉터 '{selector}' 오류: {str(e)}")
                    continue
            
            # 상품을 찾지 못한 경우 페이지 소스 분석
            if not product_elements:
                self.logger.info("🔍 상품을 찾지 못함. 페이지 분석 중...")
                
                # 현재 URL 확인
                current_url = self.driver.current_url
                self.logger.info(f"📍 현재 URL: {current_url}")
                
                # 페이지 소스에서 링크 찾기
                page_source = self.driver.page_source
                
                # 페이지 소스 일부 저장 (디버깅용)
                debug_file = self.export_dir / "designers_page_debug.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                self.logger.info(f"🐛 디버깅용 페이지 저장: {debug_file}")
                
                # 일반적인 a 태그 찾기
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                product_links = []
                
                for link in all_links:
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    
                    # 상품 링크로 보이는 것들 필터링
                    if href and any(pattern in href.lower() for pattern in ['/women/', '/men/', '/designers/', 'product']):
                        if text and len(text) > 3:  # 의미있는 텍스트가 있는 링크
                            product_links.append(link)
                
                if product_links:
                    self.logger.info(f"🔍 일반 링크에서 {len(product_links)}개 상품 후보 발견")
                    product_elements = product_links[:10]  # 최대 10개만
                else:
                    self.logger.error("❌ 어떤 방법으로도 상품 링크를 찾을 수 없음")
                    return []
            
            self.logger.info(f"📦 최종적으로 {len(product_elements)}개 상품 링크 수집")
            
            return product_elements
            
        except Exception as e:
            self.logger.error(f"❌ 상품 페이지 이동 오류: {str(e)}")
            return []

    def extract_product_data(self, product_element, index):
        """개별 상품 데이터 추출"""
        try:
            self.logger.info(f"📊 상품 {index+1} 데이터 추출 시작...")
            
            # 상품 링크 정보
            product_url = product_element.get_attribute("href")
            product_name = product_element.text.strip()
            
            self.logger.info(f"   📝 상품명: {product_name}")
            self.logger.info(f"   🔗 URL: {product_url}")
            
            # 상품 상세 페이지로 이동
            original_window = self.driver.current_window_handle
            self.driver.execute_script("window.open(arguments[0]);", product_url)
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # 페이지 로딩 대기
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # 기본 상품 데이터
            product_data = {
                'url': product_url,
                'product_name': product_name,
                'extracted_at': datetime.now().isoformat(),
                'raw_data': {}
            }
            
            # 상품 상세 정보 추출
            try:
                # 브랜드 정보 (URL에서 추출)
                url_parts = product_url.split('/')
                if len(url_parts) > 5:
                    brand_from_url = url_parts[-2].replace('-', ' ').upper()
                    product_data['raw_data']['brand_from_url'] = brand_from_url
                
                # 가격 정보 추출
                price_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='price'], .price")
                prices = []
                for elem in price_elements:
                    price_text = elem.text.strip()
                    if price_text and ('€' in price_text or '$' in price_text):
                        prices.append(price_text)
                product_data['raw_data']['prices'] = prices[:3]  # 최대 3개
                
                # 사이즈/재고 정보
                try:
                    size_table = self.driver.find_element(By.TAG_NAME, "table")
                    if size_table:
                        rows = size_table.find_elements(By.TAG_NAME, "tr")
                        size_info = []
                        for row in rows[1:]:  # 헤더 제외
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 2:
                                size_data = {
                                    'size': cells[0].text.strip(),
                                    'availability': cells[1].text.strip(),
                                    'price': cells[2].text.strip() if len(cells) > 2 else ''
                                }
                                size_info.append(size_data)
                        product_data['raw_data']['size_table'] = size_info
                except:
                    product_data['raw_data']['size_table'] = []
                
                # 이미지 URL 수집
                img_elements = self.driver.find_elements(By.TAG_NAME, "img")
                images = []
                for img in img_elements:
                    src = img.get_attribute("src")
                    if src and any(keyword in src.lower() for keyword in ['product', 'catalog']):
                        images.append(src)
                product_data['raw_data']['images'] = images[:3]  # 최대 3개
                
                # 상품 설명
                try:
                    desc_selectors = ['.product-description', '.description', '.product-details']
                    for selector in desc_selectors:
                        try:
                            desc_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                            product_data['raw_data']['description'] = desc_elem.text.strip()
                            break
                        except:
                            continue
                except:
                    pass
                
            except Exception as e:
                self.logger.warning(f"⚠️ 상품 {index+1} 상세 정보 추출 중 일부 오류: {str(e)}")
            
            # 탭 닫기 및 원래 창으로 돌아가기
            self.driver.close()
            self.driver.switch_to.window(original_window)
            
            self.logger.info(f"✅ 상품 {index+1} 데이터 추출 완료")
            return product_data
            
        except Exception as e:
            self.logger.error(f"❌ 상품 {index+1} 데이터 추출 오류: {str(e)}")
            # 안전하게 원래 창으로 돌아가기
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return None

    def save_to_json(self):
        """JSON 파일로 저장"""
        try:
            self.logger.info(f"💾 JSON 파일 저장 시작: {self.output_json}")
            
            save_data = {
                'crawl_info': {
                    'retailer_code': 'IT-T-02',
                    'retailer_name': 'TIZIANA FAUSTI',
                    'crawl_date': datetime.now().isoformat(),
                    'total_products': len(self.sample_products),
                    'purpose': 'sample_data_analysis',
                    'method': 'selenium_crawler'
                },
                'products': self.sample_products
            }
            
            with open(self.output_json, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ JSON 저장 완료: {len(self.sample_products)}개 상품")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ JSON 저장 오류: {str(e)}")
            return False

    def run_sample_crawl(self, target_count=5):
        """샘플 크롤링 실행"""
        try:
            self.logger.info(f"🎯 샘플 크롤링 시작 (목표: {target_count}개)")
            
            # 1. 드라이버 설정
            if not self.setup_driver():
                return False
            
            # 2. 로그인
            if not self.login():
                return False
            
            # 3. 상품 페이지로 이동
            product_elements = self.navigate_to_products()
            if not product_elements:
                return False
            
            # 4. 샘플 상품 데이터 수집
            collected_count = 0
            for i, product_element in enumerate(product_elements):
                if collected_count >= target_count:
                    break
                
                self.logger.info(f"📦 상품 처리 중: {collected_count+1}/{target_count}")
                
                product_data = self.extract_product_data(product_element, i)
                if product_data:
                    self.sample_products.append(product_data)
                    collected_count += 1
                    self.logger.info(f"✅ 상품 {collected_count}개 수집 완료")
                
                # 요청 간격
                time.sleep(2)
            
            # 5. JSON 저장
            if self.sample_products:
                self.save_to_json()
                self.logger.info(f"🎉 샘플 크롤링 완료! 총 {len(self.sample_products)}개 상품 수집")
                return True
            else:
                self.logger.error("❌ 수집된 상품 데이터가 없습니다")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 크롤링 실행 오류: {str(e)}")
            return False
        
        finally:
            # 드라이버 종료
            if self.driver:
                self.driver.quit()
                self.logger.info("🔒 브라우저 종료")

# 실행 예시
if __name__ == "__main__":
    # 크롤러 초기화 및 실행
    crawler = TizianaSeleniumCrawler()
    
    # 샘플 크롤링 실행
    success = crawler.run_sample_crawl(target_count=5)
    
    if success:
        print(f"\n✅ 크롤링 완료! 결과 파일: {crawler.output_json}")
    else:
        print("\n❌ 크롤링 실패!")