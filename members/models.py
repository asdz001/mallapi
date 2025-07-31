from django.db import models

class Member(models.Model):
    MEMBER_TYPE_CHOICES = (
        ('B2C', '일반회원'),
        ('B2B', '사업자회원'),
    )

    # ✅ 로그인용
    username = models.CharField(max_length=30, unique=True)  # 아이디
    password = models.CharField(max_length=128)  # 암호화된 비밀번호

    # ✅ 공통 정보
    name = models.CharField(max_length=100)  # 이름
    email = models.EmailField(blank=True, null=True)  # 이메일은 필수가 아님
    phone = models.CharField(max_length=20, blank=True)  # 휴대폰
    home_phone = models.CharField(max_length=20, blank=True, null=True)  # 🏠 집전화
    address = models.CharField(max_length=255, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    member_type = models.CharField(max_length=3, choices=MEMBER_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # ✅ B2C 전용
    gender = models.CharField(max_length=1, choices=[('M', '남자'), ('F', '여자')], blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    nickname = models.CharField(max_length=30, blank=True, null=True)
    marketing_agree = models.BooleanField(default=False)
    point = models.PositiveIntegerField(default=0)
    recommender_id = models.CharField(max_length=30, blank=True, null=True)  # 추천인 아이디
    join_channel = models.CharField(max_length=20, default='direct')  # direct, naver, kakao 등
    is_forever_member = models.BooleanField(default=False, verbose_name="평생회원 여부")
    is_sms_agree = models.BooleanField(default=True, verbose_name="SMS 수신 동의")
    is_blacklisted = models.BooleanField(default=False, verbose_name="불량회원 여부")
    memo = models.TextField(blank=True, null=True, verbose_name="운영 메모")

    # ✅ B2B 전용
    company_name = models.CharField(max_length=255, blank=True, null=True)
    business_number = models.CharField(max_length=50, blank=True, null=True)
    representative_name = models.CharField(max_length=100, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    business_item = models.CharField(max_length=100, blank=True, null=True)
    fax = models.CharField(max_length=20, blank=True, null=True)
    company_phone = models.CharField(max_length=20, blank=True, null=True)
    company_address = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"[{self.member_type}] {self.username} ({self.name})"
