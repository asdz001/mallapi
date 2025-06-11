# 📁 shop/api/eleonorabonucci/fetch_articles.py

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# 🛡️ 엘레오노라 API Key
API_KEY = "da3e1b50-8ce1-433d-a7a5-6353b0c969d3"

# 🔗 API의 공통 주소
BASE_URL = "https://api.eleonorabonucci.com/Api/Article"


# ✅ 시즌 목록 수집 (ex: ["SS24", "FW24", ...])
def fetch_season_list():
    url = f"{BASE_URL}/GetSeason"
    params = {"Cod": API_KEY}
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"❌ 시즌 수집 실패: {response.status_code}")
        return []

    seasons = response.json()
    print(f"✅ 시즌 목록: {seasons}")
    return seasons


# ✅ 시즌별 페이지 수 확인
def fetch_total_pages(season_code):
    url = f"{BASE_URL}/Pages"
    params = {"Cod": API_KEY, "season": season_code}
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"❌ 시즌 '{season_code}' 페이지 수 실패")
        return 0

    total_pages = response.json().get("TotalPages", 0)
    print(f"📘 시즌 {season_code} → 총 {total_pages} 페이지")
    return total_pages


# ✅ 상품 수집 함수 (시즌 + 페이지 조합으로 1페이지 요청)
def fetch_article_page(season, page):
    url = f"{BASE_URL}/Get"
    params = {"Cod": API_KEY, "Season": season, "Pages": str(page)}
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"❌ 실패: 시즌={season}, 페이지={page}")
        return []

    data = response.json()
    articles = data.get("ARTICLE", [])
    print(f"📦 수집됨 → 시즌 {season} / 페이지 {page} → {len(articles)}개")
    return articles


# ✅ 모든 시즌 전체 페이지에서 상품 수집 (병렬처리)
def fetch_all_articles(max_workers=10):
    all_articles = []
    seasons = fetch_season_list()

    for season in seasons:
        total_pages = fetch_total_pages(season)
        if total_pages == 0:
            continue

        futures = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for page in range(1, total_pages + 1):
                # 시즌, 페이지 쌍을 병렬로 수집
                futures.append(executor.submit(fetch_article_page, season, page))

            for future in as_completed(futures):
                articles = future.result()
                all_articles.extend(articles)

    print(f"\n🎯 전체 수집된 상품 수: {len(all_articles)}개")
    return all_articles


# ✅ 실행 시 동작
if __name__ == "__main__":
    fetch_all_articles(max_workers=10)
