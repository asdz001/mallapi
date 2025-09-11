# promotion/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import string
import random

class PromotionRule(models.Model):
    """
    🎯 프로모션 전체 규칙 설정
    - 할인 적용 순서 및 중복 허용 여부 관리
    """
    
    name = models.CharField(
        max_length=100,
        verbose_name="규칙명",
        help_text="예: 기본 할인 규칙"
    )
    
    # 할인 적용 순서 설정
    PRIORITY_ORDER_CHOICES = [
        ('grade_first', '등급할인 → 쿠폰 → 이벤트'),
        ('coupon_first', '쿠폰 → 등급할인 → 이벤트'),
        ('best_discount', '가장 유리한 할인 자동선택'),
    ]
    
    priority_order = models.CharField(
        max_length=20,
        choices=PRIORITY_ORDER_CHOICES,
        default='grade_first',
        verbose_name="할인 적용 순서"
    )
    
    # 중복 허용 설정
    allow_coupon_stack = models.BooleanField(
        default=False,
        verbose_name="쿠폰 중복사용 허용",
        help_text="여러 쿠폰 동시 사용 가능 여부"
    )
    
    allow_grade_coupon_stack = models.BooleanField(
        default=True,
        verbose_name="등급할인+쿠폰 중복 허용",
        help_text="등급할인과 쿠폰할인 동시 적용 가능"
    )
    
    max_discount_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="최대 할인율(%)",
        help_text="전체 할인의 최대 한도"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "프로모션 규칙"
        verbose_name_plural = "프로모션 규칙"
    
    def __str__(self):
        return self.name


class Coupon(models.Model):
    """
    🎫 쿠폰 시스템
    - 개별 코드 기반 할인
    - 정액/정률 할인 지원
    """
    
    # 기본 정보
    name = models.CharField(
        max_length=100,
        verbose_name="쿠폰명",
        help_text="관리자용 쿠폰 이름"
    )
    
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="쿠폰 코드",
        help_text="사용자가 입력할 쿠폰 코드"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="설명",
        help_text="쿠폰에 대한 상세 설명"
    )
    
    # 할인 설정
    DISCOUNT_TYPE_CHOICES = [
        ('fixed', '정액할인'), # 5000원 할인
        ('percent', '정률할인'), # 10% 할인
    ]
    
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default='fixed',
        verbose_name="할인 타입"
    )
    
    discount_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="할인 값",
        help_text="정액할인: 원 단위, 정률할인: % 단위"
    )
    
    max_discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="최대 할인 금액",
        help_text="정률할인 시 최대 할인 한도 (원)"
    )
    
    # 사용 조건
    min_purchase_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="최소 구매금액",
        help_text="쿠폰 사용을 위한 최소 주문 금액"
    )
    
    # 사용 제한
    usage_limit = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="총 사용 제한",
        help_text="전체 사용 가능 횟수 (미입력시 무제한)"
    )
    
    usage_limit_per_user = models.IntegerField(
        default=1,
        verbose_name="회원별 사용 제한",
        help_text="한 회원이 사용할 수 있는 최대 횟수"
    )
    
    # 유효 기간
    start_date = models.DateTimeField(
        verbose_name="시작일시",
        help_text="쿠폰 사용 가능 시작 시간"
    )
    
    end_date = models.DateTimeField(
        verbose_name="종료일시",
        help_text="쿠폰 사용 만료 시간"
    )
    
    # 대상 제한
    target_member_types = models.CharField(
        max_length=20,
        choices=[
            ('all', '모든 회원'),
            ('B2C', 'B2C 회원만'),
            ('B2B', 'B2B 회원만'),
        ],
        default='all',
        verbose_name="대상 회원"
    )
    
    target_grades = models.ManyToManyField(
        'members.MemberGrade',
        blank=True,
        verbose_name="대상 등급",
        help_text="특정 등급만 사용 가능 (미선택시 모든 등급)"
    )
    
    # 상태 관리
    is_active = models.BooleanField(
        default=True,
        verbose_name="활성화"
    )
    
    # 통계 필드 (자동 계산)
    used_count = models.IntegerField(
        default=0,
        verbose_name="사용 횟수",
        help_text="자동 계산되는 총 사용 횟수"
    )
    
    # 시스템 필드
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="생성자"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "쿠폰"
        verbose_name_plural = "쿠폰"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @classmethod
    def generate_code(cls, length=8):
        """랜덤 쿠폰 코드 생성"""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choice(chars) for _ in range(length))
            if not cls.objects.filter(code=code).exists():
                return code
    
    def is_valid(self, user=None):
        """쿠폰 유효성 검사"""
        now = timezone.now()
        
        # 기간 체크
        if now < self.start_date or now > self.end_date:
            return False, "사용 기간이 아닙니다"
        
        # 활성화 체크
        if not self.is_active:
            return False, "비활성화된 쿠폰입니다"
        
        # 사용 제한 체크
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, "사용 가능 횟수를 초과했습니다"
        
        # 회원별 사용 제한 체크
        if user:
            user_usage = CouponUsage.objects.filter(
                coupon=self,
                user=user
            ).count()
            
            if user_usage >= self.usage_limit_per_user:
                return False, "개인 사용 한도를 초과했습니다"
        
        return True, "사용 가능"
    
    def calculate_discount(self, amount):
        """할인 금액 계산"""
        if self.discount_type == 'fixed':
            # 정액할인
            return min(Decimal(str(self.discount_value)), amount)
        
        elif self.discount_type == 'percent':
            # 정률할인
            discount = amount * (Decimal(str(self.discount_value)) / 100)
            if self.max_discount_amount:
                discount = min(discount, Decimal(str(self.max_discount_amount)))
            return discount
        
        return Decimal('0')


class Event(models.Model):
    """
    🎉 이벤트 할인 시스템
    - 기간 한정 전체/카테고리별 할인
    """
    
    name = models.CharField(
        max_length=100,
        verbose_name="이벤트명"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="이벤트 설명"
    )
    
    # 할인 설정
    discount_type = models.CharField(
        max_length=10,
        choices=Coupon.DISCOUNT_TYPE_CHOICES,
        default='percent',
        verbose_name="할인 타입"
    )
    
    discount_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="할인 값"
    )
    
    max_discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="최대 할인 금액"
    )
    
    # 적용 대상
    target_all_products = models.BooleanField(
        default=True,
        verbose_name="전체 상품 적용"
    )
    
    target_categories = models.JSONField(
        default=list,
        blank=True,
        verbose_name="대상 카테고리",
        help_text="특정 카테고리만 적용할 경우"
    )
    
    target_brands = models.JSONField(
        default=list,
        blank=True,
        verbose_name="대상 브랜드",
        help_text="특정 브랜드만 적용할 경우"
    )
    
    # 기간 설정
    start_date = models.DateTimeField(verbose_name="시작일시")
    end_date = models.DateTimeField(verbose_name="종료일시")
    
    # 조건
    min_purchase_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="최소 구매금액"
    )
    
    # 우선순위 (낮을수록 먼저 적용)
    priority = models.IntegerField(
        default=100,
        verbose_name="우선순위",
        help_text="낮은 숫자가 높은 우선순위"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "이벤트 할인"
        verbose_name_plural = "이벤트 할인"
        ordering = ['priority', '-created_at']
    
    def __str__(self):
        return self.name
    
    def is_valid(self):
        """이벤트 유효성 검사"""
        now = timezone.now()
        return (
            self.is_active and 
            self.start_date <= now <= self.end_date
        )
    
    def calculate_discount(self, amount):
        """할인 금액 계산 (쿠폰과 동일한 로직)"""
        if self.discount_type == 'fixed':
            return min(Decimal(str(self.discount_value)), amount)
        elif self.discount_type == 'percent':
            discount = amount * (Decimal(str(self.discount_value)) / 100)
            if self.max_discount_amount:
                discount = min(discount, Decimal(str(self.max_discount_amount)))
            return discount
        return Decimal('0')


class CouponUsage(models.Model):
    """
    🎫 쿠폰 사용 내역
    - 사용 추적 및 통계용
    """
    
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name='usages',
        verbose_name="쿠폰"
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="사용자"
    )
    
    # 사용 정보
    order_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="주문번호",
        help_text="향후 주문 시스템 연동용"
    )
    
    original_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name="원래 금액"
    )
    
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name="할인 금액"
    )
    
    final_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name="최종 금액"
    )
    
    used_at = models.DateTimeField(auto_now_add=True, verbose_name="사용일시")
    
    # 상태 추적
    STATUS_CHOICES = [
        ('used', '사용됨'),
        ('cancelled', '취소됨'),  # 주문 취소 시
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='used',
        verbose_name="상태"
    )
    
    class Meta:
        verbose_name = "쿠폰 사용내역"
        verbose_name_plural = "쿠폰 사용내역"
        ordering = ['-used_at']
    
    def __str__(self):
        return f"{self.coupon.code} - {self.user.username} ({self.used_at.date()})"


# 시그널을 통한 자동 업데이트
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=CouponUsage)
def update_coupon_usage_count(sender, instance, created, **kwargs):
    """쿠폰 사용 시 사용 횟수 자동 업데이트"""
    if created and instance.status == 'used':
        instance.coupon.used_count = CouponUsage.objects.filter(
            coupon=instance.coupon,
            status='used'
        ).count()
        instance.coupon.save()