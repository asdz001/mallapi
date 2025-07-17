from django.db import models
from multiselectfield import MultiSelectField
from django.contrib.auth.models import User



#거래처
class Retailer(models.Model):
    name = models.CharField(max_length=100, verbose_name="업체명")  # 사람이 보는 이름
    code = models.CharField(max_length=50, unique=True, verbose_name="업체코드")  # 매칭용 키 (예: RATTI, GAUDENZI)

    order_api_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="주문용 리테일러명")
    last_fetch_started_at = models.DateTimeField(null=True, blank=True, verbose_name="수집 시작 시간")
    last_fetch_finished_at = models.DateTimeField(null=True, blank=True, verbose_name="수집 완료 시간")
    last_register_finished_at = models.DateTimeField(null=True, blank=True, verbose_name="등록 완료 시간")
    last_fetched_count = models.PositiveIntegerField(default=0, verbose_name="수집 상품 수")
    last_registered_count = models.PositiveIntegerField(default=0, verbose_name="등록 상품 수")
    auto_schedule = models.CharField(max_length=100, blank=True, null=True,verbose_name="⏰ 자동 스케줄")
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_%(class)s")
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_%(class)s")
    is_running = models.BooleanField(default=False)



    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = "거래처"
        verbose_name_plural = "1. 거래처"




#브랜드명
class BrandSetting(models.Model):
    """
    브랜드 기본 설정 (거래처+브랜드+시즌+우선순위)
    """
    
    # 기본 정보
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE, verbose_name="거래처")
    brand_name = models.CharField(max_length=100, verbose_name="브랜드명", 
                                help_text="특정 브랜드명 또는 '전체', 'ETC'")
    seasons = models.TextField(blank=True, null=True, verbose_name="시즌",
                             help_text="시즌을 쉼표로 구분하여 입력 (예: FW25,SS25,CARRYOVER)")
    
    # 우선순위
    priority = models.IntegerField(default=1, verbose_name="우선순위",
                                 help_text="1=최우선, 숫자가 클수록 후순위")
    
    # 메타 정보
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    description = models.TextField(blank=True, null=True, verbose_name="설명",
                                 help_text="이 설정에 대한 설명")
    
    # 추적 정보
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, 
                                 related_name="created_brand_settings")
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="updated_brand_settings")
    
    def get_season_list(self):
        """시즌 문자열을 리스트로 변환"""
        if not self.seasons:
            return []
        # 다양한 구분자 지원 (쉼표, 파이프, 슬래시)
        seasons_str = self.seasons.replace('|', ',').replace('/', ',')
        return [s.strip() for s in seasons_str.split(',') if s.strip()]
    
    def season_display(self):
        """시즌을 보기 좋게 표시"""
        seasons = self.get_season_list()
        return " | ".join(seasons) if seasons else "-"
    
    def markup_count(self):
        """설정된 마크업 개수"""
        return self.markups.count()
    
    def markup_summary(self):
        """마크업 요약 정보"""
        markups = self.markups.all()
        if not markups:
            return "마크업 없음"
        
        summary = []
        for markup in markups[:3]:  # 최대 3개만 표시
            summary.append(f"{markup.gender}·{markup.category}: {markup.markup}")
        
        if markups.count() > 3:
            summary.append(f"외 {markups.count() - 3}개")
            
        return " | ".join(summary)
    
    def matches_product(self, product, gender=None, category=None):
        """상품이 이 설정과 매치되는지 확인"""
        # 거래처 체크
        if self.retailer.code != product.retailer:
            return False
            
        # 브랜드 체크 (전체, ETC는 모든 브랜드와 매치)
        if self.brand_name not in ['전체', 'ETC']:
            if self.brand_name != product.raw_brand_name:
                return False
        
        # 시즌 체크
        if self.seasons and product.season:
            season_list = self.get_season_list()
            if product.season not in season_list:
                return False
                
        return True
    
    def get_markup_for_product(self, product):
        """상품에 맞는 마크업 반환"""
        # 정확한 성별+카테고리 매치 시도
        markup_detail = self.markups.filter(
            gender=product.gender,
            category=product.category1
        ).first()
        
        if markup_detail:
            return markup_detail.markup
            
        # 전체 성별 매치 시도
        markup_detail = self.markups.filter(
            gender='전체',
            category=product.category1
        ).first()
        
        if markup_detail:
            return markup_detail.markup
            
        # 전체 카테고리 매치 시도
        markup_detail = self.markups.filter(
            gender=product.gender,
            category='전체'
        ).first()
        
        if markup_detail:
            return markup_detail.markup
            
        # 전체+전체 매치 시도
        markup_detail = self.markups.filter(
            gender='전체',
            category='전체'
        ).first()
        
        if markup_detail:
            return markup_detail.markup
            
        return None
    
    def __str__(self):
        return f"{self.retailer.code} | {self.brand_name} | {self.season_display()}"
    
    class Meta:
        verbose_name = "브랜드정리"
        verbose_name_plural = "3. 브랜드정리"
        ordering = ['retailer', 'priority', 'brand_name']
        # 같은 거래처+브랜드+시즌+우선순위는 중복 불가
        unique_together = ['retailer', 'brand_name', 'seasons', 'priority']


class BrandMarkupDetail(models.Model):
    """
    브랜드별 성별+카테고리별 세부 마크업 설정
    """
    
    GENDER_CHOICES = [
        ('남성', '남성'),
        ('여성', '여성'), 
        ('키즈', '키즈'),
        ('라이프', '라이프'),
        ('전체', '전체'),
    ]
    
    CATEGORY_CHOICES = [
        ('의류', '의류'),
        ('신발', '신발'),
        ('가방', '가방'),
        ('액세서리', '액세서리'),
        ('전체', '전체'),
    ]
    
    # 관계
    brand_setting = models.ForeignKey(BrandSetting, on_delete=models.CASCADE, 
                                    related_name='markups', verbose_name="브랜드 설정")
    
    # 세부 조건
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name="성별")
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, verbose_name="카테고리")
    
    # 마크업
    markup = models.FloatField(verbose_name="마크업율")
    
    # 메타 정보
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.brand_setting.brand_name} | {self.gender} | {self.category} | {self.markup}"
    
    class Meta:
        verbose_name = "세부 마크업"
        verbose_name_plural = "세부 마크업"
        ordering = ['brand_setting', 'gender', 'category']
        # 같은 브랜드 설정 내에서 성별+카테고리 조합은 중복 불가
        unique_together = ['brand_setting', 'gender', 'category']



#FTA적용여부
class FixedCountry(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="표준국가명")
    fta_applicable = models.BooleanField(default=False, verbose_name="FTA 적용 여부")

    def __str__(self):
        return f"{self.name} (FTA 적용: {'O' if self.fta_applicable else 'X'})"


    class Meta:
        verbose_name = "FTA적용여부"
        verbose_name_plural = "4. FTA적용여부"


# 거래처별 원산지 표현 매핑
class CountryAlias(models.Model):
    origin_name = models.CharField(max_length=100, unique=True, verbose_name="원본국가명")  # 거래처 원본 표기
    standard_country = models.ForeignKey(FixedCountry, on_delete=models.CASCADE, verbose_name="표준국가")

    def __str__(self):
        return f"{self.origin_name} → {self.standard_country.name}"
    
    




#표준준계산식
class GlobalPricingSetting(models.Model):
    exchange_rate = models.FloatField(default=1450, verbose_name="환율(원화)")
    shipping_fee = models.FloatField(default=0, verbose_name="배송비(%)")
    VAT = models.FloatField(default=1.1, verbose_name="부가세율(%)")
    margin_rate = models.FloatField(default=1.3, verbose_name="마진율(%)")
    special_tax_rate = models.FloatField(default=0.0, verbose_name="개소세율(%)")

    def __str__(self):
        return "전역 가격 계산 설정"


    class Meta:
        verbose_name = "표준계산식"
        verbose_name_plural = "1. 표준계산식"

class PriceFormulaRange(models.Model):
    setting = models.ForeignKey(GlobalPricingSetting, on_delete=models.CASCADE, related_name='formula_ranges')
    min_price = models.IntegerField(verbose_name="금액범위 최소")
    max_price = models.IntegerField(verbose_name="금액범위 최대")
    formula = models.TextField(verbose_name="가격공식", help_text="예: 가격 * 0.05 + 10000")

    def __str__(self):
        return f"{self.min_price} ~ {self.max_price}: {self.formula}"
    




class RetailerSeasonSummary(models.Model):
    retailer_code = models.CharField(max_length=20, db_index=True)
    seasons = models.TextField(help_text="comma-separated 시즌 목록")

    class Meta:
        verbose_name = "거래처 시즌 요약"
        verbose_name_plural = "거래처 시즌 요약"

