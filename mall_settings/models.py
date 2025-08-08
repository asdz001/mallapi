# mall_settings/models.py


from django.db import models
from ckeditor.fields import RichTextField
from django.contrib.auth.models import User




# 쇼핑몰 설정
class SiteSetting(models.Model):
    site_name = models.CharField("쇼핑몰 이름", max_length=255)
    logo = models.ImageField("로고", upload_to="site/logo/", blank=True, null=True)
    contact_email = models.EmailField("대표 이메일", blank=True, null=True)
    contact_phone = models.CharField("대표 전화번호", max_length=20, blank=True)
    business_hours = models.CharField("운영 시간", max_length=255, blank=True)

    # ✅ 사업자 정보
    ceo_name = models.CharField("대표자명", max_length=100, blank=True)
    business_number = models.CharField("사업자등록번호", max_length=20, blank=True)
    commerce_number = models.CharField("통신판매업 신고번호", max_length=100, blank=True)
    business_address = models.CharField("사업장 주소", max_length=255, blank=True)
    business_license_image = models.ImageField("사업자등록증 이미지", upload_to="site/license/", blank=True, null=True)

    # ✅ 푸터
    footer_text = models.TextField("푸터 문구", blank=True)

    # 약관
    terms_of_service = RichTextField("이용약관", blank=True, null=True)
    privacy_policy = RichTextField("개인정보처리방침", blank=True, null=True)
    ecommerce_notice = RichTextField("전자상거래법 고지사항", blank=True, null=True)
    return_policy = RichTextField("청약철회/환불정책", blank=True, null=True)

    def __str__(self):
        return self.site_name






# 운영자 프로필 모델
class OperatorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # 거래처 권한 설정 (ManyToManyField)
    allowed_retailers = models.ManyToManyField('pricing.Retailer', blank=True)

    # 알림 설정
    receive_order_alerts = models.BooleanField(default=True)
    receive_stock_alerts = models.BooleanField(default=False)

    # ✅ 연락처 필드 추가
    contact_number = models.CharField("연락처", max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username} 운영자 프로필"


