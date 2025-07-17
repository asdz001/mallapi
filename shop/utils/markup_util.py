# shop/utils/markup_util.py
# 새로운 BrandSetting + BrandMarkupDetail 모델 구조에 맞춘 마크업 계산 유틸

from pricing.models import BrandSetting, BrandMarkupDetail, Retailer
from utils.markup_logger import log_markup_failure

def get_markup_from_product(product):
    """
    상품에 맞는 마크업을 검색
    성공 시: 조용히 마크업 반환
    실패 시: 로그 파일에만 기록
    
    Args:
        product: 상품 객체
        
    Returns:
        float: 마크업 값 또는 None
    """
    
    # 거래처 확인
    try:
        retailer = Retailer.objects.get(code=product.retailer)
    except Retailer.DoesNotExist:
        log_markup_failure(product, "거래처 찾을 수 없음", f"거래처 코드: {product.retailer}")
        return None
    
    # 필수값 검증 (브랜드명만 체크)
    if not product.raw_brand_name:
        log_markup_failure(product, "필수값 누락", "누락 필드: 브랜드명")
        return None
    
    # 상품 정보 추출
    product_brand = product.raw_brand_name
    product_category = product.category1 if product.category1 else None
    product_gender = getattr(product, 'gender', None)
    product_season = getattr(product, 'season', None) or '전체'
    
    # 성별 또는 카테고리 중 하나라도 빈칸이면 특별 처리
    if not product_gender or not product_category:
        markup = _get_fallback_markup(retailer, product)
        if markup is not None:
            return markup
    
    # 일반적인 마크업 검색 (기존 로직)
    product_gender = product_gender or '전체'
    product_category = product_category or '전체'
    
    # 우선순위 순으로 BrandSetting 조회
    brand_settings = BrandSetting.objects.filter(
        retailer=retailer,
        is_active=True
    ).order_by('priority', 'id')
    
    if not brand_settings.exists():
        log_markup_failure(product, "활성화된 브랜드 설정 없음", 
                         f"거래처 {retailer.code}에 활성화된 브랜드 설정이 없습니다")
        return None
    
    # 각 BrandSetting을 우선순위 순으로 검사
    for setting in brand_settings:
        # 브랜드 매칭
        if not _is_brand_match(setting.brand_name, product_brand):
            continue
        
        # 시즌 매칭
        if not _is_season_match(setting, product_season):
            continue
        
        # 성별 + 카테고리 매칭
        markup = _find_markup_detail(setting, product_gender, product_category)
        if markup is not None:
            # ✅ 성공 - 조용히 반환
            return markup
    
    # 모든 설정을 검사했지만 마크업을 찾지 못함 - 로그만 기록
    available_settings = [f"{s.priority}순위-{s.brand_name}-{s.season_display()}" for s in brand_settings]
    details = f"검색 대상: {len(brand_settings)}개 설정 | 사용 가능 설정: {', '.join(available_settings)}"
    log_markup_failure(product, "마크업 설정 매치 실패", details)
    return None


def _get_fallback_markup(retailer, product):
    """
    성별 또는 카테고리가 빈칸일 때 마지막 우선순위 설정에서 마크업 조회
    """
    # 마지막 우선순위(가장 큰 priority) 순으로 BrandSetting 조회
    brand_settings = BrandSetting.objects.filter(
        retailer=retailer,
        is_active=True
    ).order_by('-priority', '-id')  # 역순 정렬
    
    if not brand_settings.exists():
        return None
    
    # 각 BrandSetting을 마지막 우선순위부터 검사
    for setting in brand_settings:
        # 성별=전체, 카테고리=전체로 강제 검색
        markup = _find_markup_detail(setting, "전체", "전체")
        if markup is not None:
            # 특별 처리 로그 기록
            missing_fields = []
            if not getattr(product, 'gender', None):
                missing_fields.append("성별")
            if not product.category1:
                missing_fields.append("카테고리")
            
            details = f"빈칸 데이터 특별 처리 - 마지막 우선순위({setting.priority}) 설정 적용: {setting.brand_name} | 누락 필드: {', '.join(missing_fields)} → 전체+전체로 조회"
            log_markup_failure(product, "특별 처리로 마크업 적용", details)
            return markup
    
    return None


def _is_brand_match(setting_brand, product_brand):
    """브랜드 매칭 검사"""
    # "전체" 설정은 모든 브랜드와 매치
    if setting_brand == "전체":
        return True
    
    # 상품 브랜드가 빈칸이면 "전체" 설정과만 매치 (위에서 이미 처리됨)
    if not product_brand or product_brand.strip() == "":
        return False
    
    # 정확한 브랜드명 매치
    return setting_brand == product_brand


def _is_season_match(brand_setting, product_season):
    """시즌 매칭 검사"""
    # BrandSetting에 시즌이 설정되지 않은 경우 → 모든 시즌과 매치
    if not brand_setting.seasons:
        return True
    
    setting_seasons_raw = brand_setting.seasons.strip()
    
    # "전체" 시즌은 모든 시즌과 매치
    if "전체" in setting_seasons_raw:
        return True
    
    # 상품 시즌이 빈칸이면 "전체" 설정과만 매치 (위에서 이미 처리됨)
    if not product_season or product_season.strip() == "":
        return False
    
    # 쉼표로만 구분 (슬래시, 파이프는 시즌명의 일부)
    setting_seasons = [s.strip() for s in setting_seasons_raw.split(',') if s.strip()]
    return product_season in setting_seasons


def _find_markup_detail(brand_setting, product_gender, product_category):
    """성별+카테고리에 맞는 마크업 검색"""
    # 상품 성별/카테고리가 빈칸인 경우 "전체"로 처리
    if not product_gender or product_gender.strip() == "":
        product_gender = "전체"
    if not product_category or product_category.strip() == "":
        product_category = "전체"
    
    search_scenarios = [
        (product_gender, product_category),
        (product_gender, "전체"),
        ("전체", product_category),
        ("전체", "전체"),
    ]
    
    for gender, category in search_scenarios:
        try:
            markup_detail = BrandMarkupDetail.objects.filter(
                brand_setting=brand_setting,
                gender=gender,
                category=category,
                is_active=True
            ).first()
            
            if markup_detail:
                return markup_detail.markup
        except Exception:
            continue
    
    return None


def debug_product_markup(product):
    """
    개발용 디버깅 함수 (콘솔 출력 + 로그 기록)
    """
    print(f"\n🔍 마크업 디버깅: 상품 ID {getattr(product, 'id', 'Unknown')}")
    print(f"   상품: {product.retailer} | {product.raw_brand_name} | {getattr(product, 'season', None)} | {getattr(product, 'gender', None)} | {product.category1}")
    
    # 빈칸 체크
    product_gender = getattr(product, 'gender', None)
    product_category = product.category1
    
    if not product_gender or not product_category:
        print(f"   🚨 빈칸 감지: 성별={product_gender}, 카테고리={product_category} → 특별 처리 모드")
    
    markup = get_markup_from_product(product)
    
    if markup is not None:
        print(f"   결과: ✅ 마크업 {markup}")
    else:
        print(f"   결과: ❌ 마크업 없음 (로그 파일 확인)")
    
    return markup