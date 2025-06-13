from django.db import models
from multiselectfield import MultiSelectField



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
    is_running = models.BooleanField(default=False)



    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = "거래처"
        verbose_name_plural = "1. 거래처"




#브랜드명
class BrandSetting(models.Model):
    CATEGORY_CHOICES = [
        ('의류', '의류'),
        ('신발', '신발'),
        ('가방', '가방'),
        ('액세서리', '액세서리'),
    ]

    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE, verbose_name="거래처")
    season = models.CharField(max_length=50, blank=True, null=True, verbose_name="시즌")
    brand_name = models.CharField(max_length=100, verbose_name="브랜드명", help_text="[전체] 입력 시 모든 브랜드에 적용됨")
    category1 = MultiSelectField(choices=CATEGORY_CHOICES, verbose_name="카테고리", max_length=100)
    markup = models.FloatField(default=1.0, verbose_name="마크업율")

    def __str__(self):
        return f"{self.retailer} / {self.brand_name} / {self.category1} : {self.markup}"

    class Meta:
        verbose_name = "브랜드정리"
        verbose_name_plural = "3. 브랜드정리"



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
    




