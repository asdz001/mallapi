# members/models.py

from django.db import models
from django.utils import timezone

# ========================================
# 🔧 커스텀 매니저 클래스들
# ========================================

class ActiveMemberManager(models.Manager):
    """활성 회원만 조회하는 기본 매니저"""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class AllMemberManager(models.Manager):
    """삭제된 회원 포함 전체 조회 매니저"""
    def get_queryset(self):
        return super().get_queryset()

class DeletedMemberManager(models.Manager):
    """삭제된 회원만 조회하는 매니저"""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=True)


class Member(models.Model):
    # ========================================
    # 🔧 기존 필드들 (그대로 유지)
    # ========================================
    
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

    # ========================================
    # 🆕 소프트 삭제 관련 필드들 (새로 추가)
    # ========================================
    
    # 🗑️ 삭제 상태 관리
    is_deleted = models.BooleanField(
        default=False, 
        verbose_name="삭제 여부",
        help_text="True면 삭제된 회원으로 처리됩니다."
    )
    
    # 📅 삭제 일시
    deleted_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="삭제 일시",
        help_text="실제 삭제가 실행된 시간입니다."
    )
    
    # 👤 삭제 실행자 (관리자 아이디 또는 시스템)
    deleted_by = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="삭제 실행자",
        help_text="삭제를 실행한 관리자 아이디나 시스템명입니다."
    )
    
    # 📝 삭제 사유 (관리자가 입력)
    delete_reason = models.CharField(
        max_length=500, 
        blank=True, 
        verbose_name="삭제 사유",
        help_text="관리자가 입력한 삭제 사유입니다."
    )
    
    # 🏷️ 삭제 유형 구분
    DELETE_TYPE_CHOICES = (
        ('admin_delete', '관리자 삭제'),
        ('self_withdrawal', '회원 탈퇴'),
        ('auto_cleanup', '자동 정리'),  # 장기 미로그인 등
        ('policy_violation', '정책 위반'),  # 불량 회원 등
    )
    
    delete_type = models.CharField(
        max_length=20, 
        choices=DELETE_TYPE_CHOICES,
        blank=True, 
        verbose_name="삭제 유형",
        help_text="삭제가 발생한 경위를 구분합니다."
    )
    
    # 🔄 복구 관련 정보
    can_restore = models.BooleanField(
        default=True, 
        verbose_name="복구 가능 여부",
        help_text="False면 복구할 수 없는 삭제입니다."
    )
    
    restore_deadline = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="복구 가능 기한",
        help_text="이 날짜 이후에는 자동으로 완전삭제됩니다."
    )

    # ========================================
    # 🔧 매니저 설정 (중요: 순서가 중요함)
    # ========================================
    
    # 기본 매니저: 활성 회원만 조회
    objects = ActiveMemberManager()  # Member.objects.all() = 활성 회원만
    
    # 추가 매니저들
    all_objects = AllMemberManager()      # Member.all_objects.all() = 전체 회원
    deleted_objects = DeletedMemberManager()  # Member.deleted_objects.all() = 삭제된 회원만

    # ========================================
    # 🔧 모델 메서드들
    # ========================================
    
    def soft_delete(self, deleted_by=None, reason=None, delete_type='admin_delete'):
        """
        소프트 삭제 실행
        
        Args:
            deleted_by (str): 삭제 실행자 (관리자 아이디)
            reason (str): 삭제 사유
            delete_type (str): 삭제 유형 ('admin_delete', 'self_withdrawal' 등)
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by or 'system'
        self.delete_reason = reason or ''
        self.delete_type = delete_type
        
        # 복구 기한 설정 (30일 후)
        if delete_type in ['admin_delete', 'self_withdrawal']:
            self.restore_deadline = timezone.now() + timezone.timedelta(days=30)
        
        self.save()
    
    def restore(self, restored_by=None):
        """
        삭제된 회원 복구
        
        Args:
            restored_by (str): 복구 실행자 (관리자 아이디)
        """
        if not self.can_restore:
            raise ValueError("복구할 수 없는 회원입니다.")
        
        if self.restore_deadline and timezone.now() > self.restore_deadline:
            raise ValueError("복구 기한이 만료되었습니다.")
        
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = ''
        self.delete_reason = ''
        self.delete_type = ''
        self.restore_deadline = None
        self.save()
    
    def permanent_delete(self):
        """
        완전 삭제 (물리적 삭제)
        주의: 이 작업은 되돌릴 수 없습니다.
        """
        if not self.is_deleted:
            raise ValueError("활성 회원은 완전삭제할 수 없습니다. 먼저 소프트 삭제를 실행하세요.")
        
        # 실제 DB에서 삭제
        super().delete()
    
    def can_be_restored(self):
        """복구 가능한지 확인"""
        if not self.is_deleted or not self.can_restore:
            return False
        
        if self.restore_deadline and timezone.now() > self.restore_deadline:
            return False
        
        return True
    
    def days_until_permanent_deletion(self):
        """완전삭제까지 남은 일수"""
        if not self.restore_deadline:
            return None
        
        remaining = self.restore_deadline - timezone.now()
        return max(0, remaining.days)
    
    @property
    def delete_status_display(self):
        """삭제 상태를 한글로 표시"""
        if not self.is_deleted:
            return "활성"
        
        status_map = {
            'admin_delete': '관리자삭제',
            'self_withdrawal': '회원탈퇴',
            'auto_cleanup': '자동정리',
            'policy_violation': '정책위반',
        }
        return status_map.get(self.delete_type, '삭제됨')

    def __str__(self):
        status = " [삭제됨]" if self.is_deleted else ""
        return f"[{self.member_type}] {self.username} ({self.name}){status}"
    
    class Meta:
        # 🔧 인덱스 최적화 (성능 향상)
        indexes = [
            models.Index(fields=['is_deleted', 'created_at']),  # 목록 조회 최적화
            models.Index(fields=['deleted_at']),  # 삭제 회원 관리 최적화
            models.Index(fields=['restore_deadline']),  # 자동 정리 작업 최적화
        ]