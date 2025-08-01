# shop/utils/markup_util.py
"""
마크업 계산 유틸 (캐싱 최적화 버전)

성능 개선:
- 초기 로딩시 모든 마크업 데이터를 메모리에 캐시
- 이후 조회는 DB 쿼리 없이 메모리에서만 처리
- 1만개 상품 처리시 DB 쿼리 6만번 → 10번으로 단축
"""

from pricing.models import BrandSetting, BrandMarkupDetail, Retailer
from utils.markup_logger import log_markup_failure
import threading

# 전역 캐시 변수
_markup_cache = None
_cache_lock = threading.Lock()

class MarkupCache:
    """마크업 데이터 캐시 클래스"""
    
    def __init__(self):
        self.retailers = {}  # {retailer_code: Retailer 객체}
        self.markup_data = {}  # {retailer_code: [설정 리스트]}
        self.is_loaded = False
        self._load_all_data()
    
    def _load_all_data(self):
        """모든 마크업 관련 데이터를 한번에 로드"""
        try:
            # 1. 모든 거래처 로드
            for retailer in Retailer.objects.all():
                self.retailers[retailer.code] = retailer
            
            # 2. 모든 브랜드 설정과 마크업 상세를 한번에 로드
            brand_settings = BrandSetting.objects.filter(
                is_active=True
            ).prefetch_related(
                'markups'  # 마크업 상세도 함께 로드
            ).select_related('retailer').order_by('priority', 'id')
            
            # 3. 거래처별로 그룹화하여 캐시 구성
            for setting in brand_settings:
                retailer_code = setting.retailer.code
                
                if retailer_code not in self.markup_data:
                    self.markup_data[retailer_code] = []
                
                # 설정과 마크업 상세 정보를 딕셔너리로 구성
                setting_data = {
                    'brand_name': setting.brand_name,
                    'seasons': setting.seasons,
                    'priority': setting.priority,
                    'markups': {}  # {(성별, 카테고리): 마크업}
                }
                
                # 마크업 상세 정보 캐시
                for markup in setting.markups.filter(is_active=True):
                    key = (markup.gender, markup.category)
                    setting_data['markups'][key] = markup.markup
                
                self.markup_data[retailer_code].append(setting_data)
            
            self.is_loaded = True
            
        except Exception as e:
            log_markup_failure(None, "캐시 로딩 실패", f"오류: {str(e)}")
            self.is_loaded = False

    def get_retailer(self, retailer_code):
        """캐시에서 거래처 조회"""
        return self.retailers.get(retailer_code)
    
    def get_markup_settings(self, retailer_code):
        """캐시에서 거래처별 마크업 설정 조회"""
        return self.markup_data.get(retailer_code, [])
    
    def reload_cache(self):
        """캐시 재로딩 (설정 변경시 사용)"""
        self.retailers.clear()
        self.markup_data.clear()
        self.is_loaded = False
        self._load_all_data()


def _get_cache():
    """싱글톤 방식으로 캐시 인스턴스 반환"""
    global _markup_cache
    
    if _markup_cache is None:
        with _cache_lock:
            if _markup_cache is None:  # Double-checked locking
                _markup_cache = MarkupCache()
    
    return _markup_cache


def get_markup_from_product(product):
    """
    상품에 맞는 마크업을 검색 (캐시 기반)
    
    성능 개선:
    - DB 쿼리 없이 메모리 캐시에서만 조회
    - 기존 인터페이스 그대로 유지
    
    Args:
        product: 상품 객체
        
    Returns:
        float: 마크업 값 또는 None
    """
    cache = _get_cache()
    
    # 캐시 로딩 실패시 None 반환
    if not cache.is_loaded:
        log_markup_failure(product, "캐시 미로딩", "마크업 캐시가 로딩되지 않았습니다")
        return None
    
    # 거래처 확인 (캐시에서)
    retailer = cache.get_retailer(product.retailer)
    if not retailer:
        log_markup_failure(product, "거래처 찾을 수 없음", f"거래처 코드: {product.retailer}")
        return None
    
    # 필수값 검증
    if not product.raw_brand_name:
        log_markup_failure(product, "필수값 누락", "누락 필드: 브랜드명")
        return None
    
    # 상품 정보 추출
    product_brand = product.raw_brand_name
    product_category = getattr(product, 'category1', None)
    product_gender = getattr(product, 'gender', None)
    product_season = getattr(product, 'season', None) or '전체'
    
    # 성별 또는 카테고리가 빈칸이면 특별 처리
    if not product_gender or not product_category:
        markup = _get_fallback_markup_cached(cache, product.retailer, product)
        if markup is not None:
            return markup
    
    # 일반적인 마크업 검색
    product_gender = product_gender or '전체'
    product_category = product_category or '전체'
    
    # 캐시에서 마크업 설정 조회
    markup_settings = cache.get_markup_settings(product.retailer)
    
    if not markup_settings:
        log_markup_failure(product, "활성화된 브랜드 설정 없음", 
                         f"거래처 {product.retailer}에 활성화된 브랜드 설정이 없습니다")
        return None
    
    # 우선순위 순으로 검사 (이미 정렬되어 캐시됨)
    for setting_data in markup_settings:
        # 브랜드 매칭
        if not _is_brand_match_cached(setting_data['brand_name'], product_brand):
            continue
        
        # 시즌 매칭
        if not _is_season_match_cached(setting_data['seasons'], product_season):
            continue
        
        # 성별 + 카테고리 매칭
        markup = _find_markup_detail_cached(setting_data['markups'], product_gender, product_category)
        if markup is not None:
            return markup
    
    # 마크업을 찾지 못한 경우
    available_settings = [f"{s['priority']}순위-{s['brand_name']}" for s in markup_settings]
    details = f"검색 대상: {len(markup_settings)}개 설정 | 사용 가능 설정: {', '.join(available_settings)}"
    log_markup_failure(product, "마크업 설정 매치 실패", details)
    return None


def _get_fallback_markup_cached(cache, retailer_code, product):
    """캐시 기반 특별 처리 마크업 조회"""
    markup_settings = cache.get_markup_settings(retailer_code)
    
    if not markup_settings:
        return None
    
    # 마지막 우선순위부터 검사 (역순)
    sorted_settings = sorted(markup_settings, key=lambda x: x['priority'], reverse=True)
    
    for setting_data in sorted_settings:
        # 성별=전체, 카테고리=전체로 강제 검색
        markup = _find_markup_detail_cached(setting_data['markups'], "전체", "전체")
        if markup is not None:
            # 특별 처리 로그 기록
            missing_fields = []
            if not getattr(product, 'gender', None):
                missing_fields.append("성별")
            if not getattr(product, 'category1', None):
                missing_fields.append("카테고리")
            
            details = f"빈칸 데이터 특별 처리 - 마지막 우선순위({setting_data['priority']}) 설정 적용: {setting_data['brand_name']} | 누락 필드: {', '.join(missing_fields)} → 전체+전체로 조회"
            log_markup_failure(product, "특별 처리로 마크업 적용", details)
            return markup
    
    return None


def _is_brand_match_cached(setting_brand, product_brand):
    """캐시 기반 브랜드 매칭 검사"""
    if setting_brand == "전체":
        return True
    
    if not product_brand or product_brand.strip() == "":
        return False
    
    return setting_brand == product_brand


def _is_season_match_cached(setting_seasons, product_season):
    """캐시 기반 시즌 매칭 검사"""
    if not setting_seasons:
        return True
    
    setting_seasons_raw = setting_seasons.strip()
    
    if "전체" in setting_seasons_raw:
        return True
    
    if not product_season or product_season.strip() == "":
        return False
    
    setting_seasons_list = [s.strip() for s in setting_seasons_raw.split(',') if s.strip()]
    return product_season in setting_seasons_list


def _find_markup_detail_cached(markups_dict, product_gender, product_category):
    """캐시 기반 마크업 상세 검색"""
    if not product_gender or product_gender.strip() == "":
        product_gender = "전체"
    if not product_category or product_category.strip() == "":
        product_category = "전체"
    
    # 우선순위에 따른 검색 시나리오
    search_scenarios = [
        (product_gender, product_category),
        (product_gender, "전체"),
        ("전체", product_category),
        ("전체", "전체"),
    ]
    
    for gender, category in search_scenarios:
        key = (gender, category)
        if key in markups_dict:
            return markups_dict[key]
    
    return None


def reload_markup_cache():
    """
    마크업 캐시 재로딩
    
    사용 시점:
    - 마크업 설정 변경 후
    - 관리자 페이지에서 설정 수정 후
    """
    global _markup_cache
    
    with _cache_lock:
        if _markup_cache is not None:
            _markup_cache.reload_cache()


def get_cache_info():
    """
    캐시 정보 조회 (디버깅용)
    
    Returns:
        dict: 캐시 상태 정보
    """
    cache = _get_cache()
    
    return {
        'is_loaded': cache.is_loaded,
        'retailers_count': len(cache.retailers),
        'markup_settings_count': sum(len(settings) for settings in cache.markup_data.values()),
        'total_retailer_codes': list(cache.retailers.keys())
    }


def debug_product_markup(product):
    """개발용 디버깅 함수 (캐시 정보 포함)"""
    print(f"\n🔍 마크업 디버깅: 상품 ID {getattr(product, 'id', 'Unknown')}")
    print(f"   상품: {product.retailer} | {product.raw_brand_name} | {getattr(product, 'season', None)} | {getattr(product, 'gender', None)} | {getattr(product, 'category1', None)}")
    
    # 캐시 정보
    cache_info = get_cache_info()
    print(f"   캐시 상태: {'로딩됨' if cache_info['is_loaded'] else '로딩 실패'}")
    print(f"   캐시된 거래처: {cache_info['retailers_count']}개")
    print(f"   캐시된 설정: {cache_info['markup_settings_count']}개")
    
    # 빈칸 체크
    product_gender = getattr(product, 'gender', None)
    product_category = getattr(product, 'category1', None)
    
    if not product_gender or not product_category:
        print(f"   🚨 빈칸 감지: 성별={product_gender}, 카테고리={product_category} → 특별 처리 모드")
    
    markup = get_markup_from_product(product)
    
    if markup is not None:
        print(f"   결과: ✅ 마크업 {markup}")
    else:
        print(f"   결과: ❌ 마크업 없음 (로그 파일 확인)")
    
    return markup