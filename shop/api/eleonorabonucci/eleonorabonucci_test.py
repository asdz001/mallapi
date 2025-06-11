import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ✅ API 설정
API_KEY = "da3e1b50-8ce1-433d-a7a5-6353b0c969d3"
BASE_URL = "https://api.eleonorabonucci.com/Api/Article"

# ✅ 저장 경로
EXPORT_DIR = Path("export") / "ELEONORA"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON = EXPORT_DIR / "eleonora_merged_raw_products.json"

# ✅ 실패 추적 리스트
failed_pages = []

# ✅ 시즌 목록 수집
def fetch_season_list():
    try:
        url = f"{BASE_URL}/GetSeason"
        params = {"Cod": API_KEY}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            seasons = response.json()
            print(f"✅ 시즌 목록: {seasons}")
            return seasons
        else:
            print(f"❌ 시즌 수집 실패: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 시즌 목록 오류: {e}")
        return []

# ✅ 시즌별 페이지 수
def fetch_total_pages(season):
    try:
        url = f"{BASE_URL}/Pages"
        params = {"Cod": API_KEY, "season": season}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            total_pages = response.json().get("TotalPages", 0)
            print(f"📘 시즌 {season} → 총 {total_pages} 페이지")
            return total_pages
        else:
            print(f"❌ 시즌 '{season}' 페이지 수 실패: {response.status_code}")
            return 0
    except Exception as e:
        print(f"❌ 페이지 수 오류 {season}: {e}")
        return 0

# ✅ 상품 1페이지 수집 (재시도 + 실패 기록)
def fetch_article_page(season, page, retries=2):
    url = f"{BASE_URL}/Get"
    params = {"Cod": API_KEY, "Season": season, "Pages": str(page)}
    
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                articles = data.get("ARTICLE", [])
                if isinstance(articles, list):
                    print(f"✅ 수집: 시즌 {season}, 페이지 {page}, 상품 {len(articles)}개")
                    return articles
                else:
                    print(f"⚠️ 잘못된 응답 형식: 시즌={season}, 페이지={page}")
            else:
                print(f"⚠️ HTTP {response.status_code}: 시즌={season}, 페이지={page}")
        except Exception as e:
            print(f"⚠️ 예외: 시즌={season}, 페이지={page}, 시도={attempt+1}, 오류={e}")
        
        # 재시도 전 대기
        if attempt < retries:
            time.sleep(1)
    
    print(f"❌ 실패: 시즌={season}, 페이지={page}")
    failed_pages.append((season, page))
    return []

# ✅ 전체 시즌 상품 수집 (병렬)
def fetch_all_articles(max_workers=10):
    all_articles = []
    seasons = fetch_season_list()
    
    if not seasons:
        print("❌ 시즌 목록이 비어있습니다.")
        return []
    
    for season in seasons:
        total_pages = fetch_total_pages(season)
        print(f"\n📘 시즌 {season} → 총 {total_pages}페이지")
        
        if total_pages == 0:
            print(f"⚠️ 페이지 수 없음: 시즌 {season}")
            continue
            
        season_articles = []
        futures = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for page in range(1, total_pages + 1):
                futures.append(executor.submit(fetch_article_page, season, page))
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    season_articles.extend(result)
        
        print(f"📦 시즌 {season} → 수집된 상품 수: {len(season_articles)}개")
        all_articles.extend(season_articles)
        
        # 시즌 간 간격 (서버 부하 방지)
        time.sleep(1)
    
    return all_articles

# ✅ 재고 전체 수집
def fetch_stock_data():
    try:
        url = f"{BASE_URL}/Stock"
        params = {"Cod": API_KEY}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            stock_items = data.get("StockItems", [])
            stock_map = {item["SKU_item"]: item["Stock"] for item in stock_items}
            print(f"✅ 재고 데이터: {len(stock_map)}개 아이템")
            return stock_map
        else:
            print(f"❌ 재고 수집 실패: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ 재고 수집 오류: {e}")
        return {}

# ✅ 가격 전체 수집
def fetch_price_data():
    try:
        url = f"{BASE_URL}/Price"
        params = {"Cod": API_KEY}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            price_items = data.get("PriceItems", [])
            price_map = {
                item["SKU_item"]: {
                    "Market_Price": item["Market_Price"],
                    "Supply_Price": item["Supply_Price"]
                } for item in price_items
            }
            print(f"✅ 가격 데이터: {len(price_map)}개 아이템")
            return price_map
        else:
            print(f"❌ 가격 수집 실패: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ 가격 수집 오류: {e}")
        return {}

# ✅ 데이터 매핑 및 저장
def merge_and_save_data(articles):
    """상품 데이터에 재고/가격 매핑 후 저장"""
    if not articles:
        print("❌ 매핑할 상품 데이터가 없습니다.")
        return 0, OUTPUT_JSON
    
    print("\n🔍 재고 데이터 수집 중...")
    stock_map = fetch_stock_data()
    
    print("\n💰 가격 데이터 수집 중...")
    price_map = fetch_price_data()
    
    # 매핑 통계
    stats = {
        'total_options': 0,
        'stock_updated': 0,
        'price_updated': 0,
        'stock_missing': 0,
        'price_missing': 0
    }
    
    print("\n🔗 데이터 매핑 중...")
    
    for product in articles:
        stock_items = product.get("Stock_Item", [])
        if not isinstance(stock_items, list):
            continue
            
        for option in stock_items:
            stats['total_options'] += 1
            sku_item = option.get("SKU_item")
            
            if not sku_item:
                continue
            
            # 재고 업데이트
            if sku_item in stock_map:
                option["Stock"] = stock_map[sku_item]
                stats['stock_updated'] += 1
            else:
                stats['stock_missing'] += 1
                # 기존 재고값이 없으면 0으로 설정
                if "Stock" not in option:
                    option["Stock"] = 0
            
            # 가격 업데이트
            if sku_item in price_map:
                price_data = price_map[sku_item]
                option["Market_Price"] = price_data.get("Market_Price", option.get("Market_Price", 0))
                option["Supply_Price"] = price_data.get("Supply_Price", option.get("Supply_Price", 0))
                stats['price_updated'] += 1
            else:
                stats['price_missing'] += 1
                # 기존 가격값이 없으면 0으로 설정
                if "Market_Price" not in option:
                    option["Market_Price"] = 0
                if "Supply_Price" not in option:
                    option["Supply_Price"] = 0
    
    # 저장
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    # 매핑 결과 출력
    print(f"\n✅ 데이터 매핑 및 저장 완료!")
    print(f"📊 매핑 통계:")
    print(f"   • 총 옵션 수: {stats['total_options']:,}개")
    print(f"   • 재고 업데이트: {stats['stock_updated']:,}개")
    print(f"   • 가격 업데이트: {stats['price_updated']:,}개")
    print(f"   • 재고 누락: {stats['stock_missing']:,}개")
    print(f"   • 가격 누락: {stats['price_missing']:,}개")
    
    if stats['total_options'] > 0:
        stock_rate = (stats['stock_updated'] / stats['total_options']) * 100
        price_rate = (stats['price_updated'] / stats['total_options']) * 100
        print(f"📈 매핑 성공률: 재고 {stock_rate:.1f}%, 가격 {price_rate:.1f}%")
    
    return len(articles), OUTPUT_JSON

# ✅ 전체 프로세스 실행
def fetch_and_merge_all():
    """전체 수집, 매핑, 저장 프로세스"""
    start_time = time.time()
    
    print("🚀 엘레노라 보누치 상품 수집 시작...")
    
    # 1. 상품 수집
    articles = fetch_all_articles(max_workers=10)
    
    if not articles:
        print("❌ 수집된 상품이 없습니다.")
        return 0, OUTPUT_JSON
    
    print(f"\n📦 총 수집된 상품: {len(articles):,}개")
    
    # 2. 재고/가격 매핑 및 저장
    product_count, output_path = merge_and_save_data(articles)
    
    elapsed_time = time.time() - start_time
    
    # 3. 최종 결과
    print(f"\n✅ 전체 프로세스 완료!")
    print(f"📦 최종 상품 수: {product_count:,}개")
    print(f"⏱️ 총 소요 시간: {elapsed_time:.1f}초")
    print(f"📁 저장 위치: {output_path}")
    
    # 4. 실패한 페이지 리포트
    if failed_pages:
        print(f"\n⚠️ 실패한 페이지: {len(failed_pages)}개")
        for season, page in failed_pages[:10]:  # 최대 10개만 표시
            print(f"   🔸 시즌={season}, 페이지={page}")
        if len(failed_pages) > 10:
            print(f"   ... 및 {len(failed_pages) - 10}개 더")
    
    return product_count, output_path

# ✅ 검증 함수
def validate_result():
    """저장된 결과 검증"""
    if not OUTPUT_JSON.exists():
        print("❌ 저장된 파일이 없습니다.")
        return
    
    try:
        with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total_products = len(data)
        total_options = 0
        options_with_stock = 0
        options_with_price = 0
        
        for product in data:
            for option in product.get("Stock_Item", []):
                total_options += 1
                if option.get("Stock") is not None:
                    options_with_stock += 1
                if option.get("Market_Price") is not None and option.get("Supply_Price") is not None:
                    options_with_price += 1
        
        print(f"\n📊 저장된 파일 검증:")
        print(f"총 상품 수: {total_products:,}개")
        print(f"총 옵션 수: {total_options:,}개")
        print(f"재고 있는 옵션: {options_with_stock:,}개 ({options_with_stock/total_options*100:.1f}%)")
        print(f"가격 있는 옵션: {options_with_price:,}개 ({options_with_price/total_options*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ 검증 중 오류: {e}")

# ✅ 실행
if __name__ == "__main__":
    print("=" * 50)
    print("🛍️ 엘레노라 보누치 상품 수집기 (수정 버전)")
    print("=" * 50)
    
    # 전체 수집 및 저장
    fetch_and_merge_all()
    
    # 결과 검증
    print("\n" + "=" * 50)
    print("🔍 결과 검증")
    print("=" * 50)
    validate_result()
    
    print("\n" + "=" * 50)
    print("✅ 프로그램 종료")
    print("=" * 50)