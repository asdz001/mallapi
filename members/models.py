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
    # 👑 등급 관련 필드들 (추가)
    # ========================================
    
    grade = models.ForeignKey(
        'MemberGrade',  # 문자열로 참조 (아직 정의되지 않은 모델)
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="회원 등급",
        help_text="현재 회원 등급"
    )
    
    grade_fixed = models.BooleanField(
        default=False,
        verbose_name="등급 고정",
        help_text="체크 시 자동 승급/강등 방지"
    )
    
    grade_fixed_reason = models.TextField(
        blank=True,
        verbose_name="등급 고정 사유",
        help_text="등급을 고정한 상세 사유"
    )
    
    grade_fixed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fixed_grade_members',
        verbose_name="등급 고정한 관리자"
    )
    
    grade_fixed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="등급 고정 일시"
    )
    
    # ========================================
    # 📊 주문 통계 필드들 (향후 주문 시스템 연동용)
    # ========================================
    
    total_orders = models.IntegerField(
        default=0,
        verbose_name="총 주문수",
        help_text="총 주문 횟수 (자동 계산)"
    )
    
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="총 구매금액",
        help_text="총 구매 금액 (자동 계산)"
    )
    
    last_order_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="최근 주문일",
        help_text="마지막 주문 날짜"
    )
    
    # ... 기존 메서드들 ...
    
    def save(self, *args, **kwargs):
        """회원 정보 저장 시 등급 관련 처리"""
        
        # 신규 회원인 경우 기본 등급 할당
        if not self.pk and not self.grade:
            default_grade = MemberGrade.get_default_grade(self.member_type)
            if default_grade:
                self.grade = default_grade
        
        # 등급 고정 처리
        if self.grade_fixed and not self.grade_fixed_at:
            self.grade_fixed_at = timezone.now()
        elif not self.grade_fixed:
            self.grade_fixed_at = None
            self.grade_fixed_reason = ''
            self.grade_fixed_by = None
        
        super().save(*args, **kwargs)
    
    def change_grade(self, new_grade, reason='manual', changed_by=None, reason_detail=''):
        """
        회원 등급 변경 (이력 기록 포함)
        
        Args:
            new_grade: 새로운 등급 (MemberGrade 객체)
            reason: 변경 사유 ('auto', 'manual', 'promotion' 등)
            changed_by: 변경한 관리자 (User 객체)
            reason_detail: 상세 사유
        """
        from django.utils import timezone
        
        old_grade = self.grade
        
        # 등급 변경
        self.grade = new_grade
        self.save()
        
        # 이력 기록
        MemberGradeHistory.objects.create(
            member=self,
            old_grade=old_grade,
            new_grade=new_grade,
            change_reason=reason,
            reason_detail=reason_detail,
            changed_by=changed_by
        )
    
    def fix_grade(self, reason='', fixed_by=None):
        """등급 고정 설정"""
        from django.utils import timezone
        
        self.grade_fixed = True
        self.grade_fixed_reason = reason
        self.grade_fixed_by = fixed_by
        self.grade_fixed_at = timezone.now()
        self.save()
    
    def unfix_grade(self):
        """등급 고정 해제"""
        self.grade_fixed = False
        self.grade_fixed_reason = ''
        self.grade_fixed_by = None
        self.grade_fixed_at = None
        self.save()
    
    def can_auto_upgrade(self):
        """자동 승급 가능 여부 확인"""
        # 등급이 고정된 경우 승급 불가
        if self.grade_fixed:
            return False
        
        # 현재 등급이 자동 승급을 허용하지 않는 경우
        if self.grade and not self.grade.auto_upgrade:
            return False
            
        return True
    
    def check_grade_upgrade(self):
        """
        등급 승급 조건 확인 및 자동 승급 처리
        주문 완료 시마다 호출되는 메서드
        """
        if not self.can_auto_upgrade():
            return False
        
        # 더 높은 등급들 중에서 승급 조건을 만족하는 등급 찾기
        available_grades = MemberGrade.objects.filter(
            member_type__in=[self.member_type, 'ALL'],
            is_active=True,
            auto_upgrade=True
        )
        
        if self.grade:
            # 현재 등급보다 높은 등급들만 확인
            available_grades = available_grades.filter(order__lt=self.grade.order)
        
        available_grades = available_grades.order_by('order')
        
        for grade in available_grades:
            if grade.can_upgrade_to(self):
                # 승급 처리
                self.change_grade(
                    new_grade=grade,
                    reason='auto',
                    reason_detail=f'자동 승급 조건 달성'
                )
                return True
        
        return False
    
    @property
    def grade_display(self):
        """등급 표시용 속성"""
        if not self.grade:
            return "등급없음"
        
        # 고정 표시 추가
        fixed_mark = " 🔒" if self.grade_fixed else ""
        return f"{self.grade.display_name}{fixed_mark}"
    
    @property
    def grade_color(self):
        """등급 색상 반환"""
        return self.grade.color_code if self.grade else '#6c757d'
    
    @property
    def grade_icon(self):
        """등급 아이콘 반환"""
        return self.grade.icon_class if self.grade else 'fas fa-user'

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





# 회원 등급 모델
class MemberGrade(models.Model):
    """
    🎯 회원 등급 마스터 테이블
    - 등급별 혜택 및 승급 조건 관리
    - B2C/B2B 구분별 등급 설정
    - 자동 승급 조건 설정
    """
    
    # 기본 등급 정보
    name = models.CharField(
        max_length=50,
        verbose_name="등급명",
        help_text="예: 브론즈, 실버, 골드, VIP"
    )
    
    display_name = models.CharField(
        max_length=50,
        verbose_name="표시명",
        help_text="화면에 표시될 등급명",
        blank=True
    )
    
    # 회원 타입별 구분
    member_type = models.CharField(
        max_length=10,
        choices=[('B2C', '일반회원'), ('B2B', '사업자회원'), ('ALL', '공통')],
        default='ALL',
        verbose_name="적용 회원타입"
    )
    
    # 등급 순서 (낮을수록 높은 등급)
    order = models.IntegerField(
        default=999,
        verbose_name="등급 순서",
        help_text="낮은 숫자일수록 높은 등급 (1=최고등급)"
    )
    
    # 혜택 설정
    discount_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="할인율 (%)",
        help_text="등급별 기본 할인율"
    )
    
    point_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.0,
        verbose_name="포인트 적립율 (%)",
        help_text="구매금액 대비 포인트 적립 비율"
    )
    
    # 자동 승급 조건
    auto_upgrade = models.BooleanField(
        default=True,
        verbose_name="자동 승급 사용",
        help_text="조건 달성 시 자동으로 등급 승급"
    )
    
    min_order_count = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="최소 주문횟수",
        help_text="승급을 위한 최소 주문 횟수"
    )
    
    min_total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="최소 총 구매금액",
        help_text="승급을 위한 최소 총 구매금액 (원)"
    )
    
    min_period_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="기간별 구매금액",
        help_text="1년간 최소 구매금액 (원)"
    )
    
    # 기본 등급 설정
    is_default = models.BooleanField(
        default=False,
        verbose_name="기본 등급",
        help_text="신규 가입시 자동 할당되는 등급"
    )
    
    # 시각적 요소
    color_code = models.CharField(
        max_length=7,
        default='#6c757d',
        verbose_name="등급 색상",
        help_text="등급 표시용 색상 코드 (예: #ff6b6b)"
    )
    
    icon_class = models.CharField(
        max_length=50,
        default='fas fa-user',
        verbose_name="아이콘 클래스",
        help_text="FontAwesome 아이콘 클래스"
    )
    
    # 시스템 필드
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "회원 등급"
        verbose_name_plural = "회원 등급"
        ordering = ['member_type', 'order', 'name']
        # 회원타입별로 등급명 중복 방지
        unique_together = ['member_type', 'name']
    
    def __str__(self):
        type_display = dict(self._meta.get_field('member_type').choices)[self.member_type]
        return f"[{type_display}] {self.display_name or self.name}"
    
    def save(self, *args, **kwargs):
        """저장 시 display_name 자동 설정"""
        if not self.display_name:
            self.display_name = self.name
        super().save(*args, **kwargs)
    
    @classmethod
    def get_default_grade(cls, member_type):
        """특정 회원타입의 기본 등급 반환"""
        return cls.objects.filter(
            member_type__in=[member_type, 'ALL'],
            is_default=True,
            is_active=True
        ).first()
    
    def can_upgrade_to(self, member):
        """특정 회원이 이 등급으로 승급 가능한지 확인"""
        if not self.auto_upgrade:
            return False
            
        # 주문 횟수 조건 확인 (향후 구현)
        if self.min_order_count:
            # member.total_orders >= self.min_order_count
            pass
            
        # 총 구매금액 조건 확인 (향후 구현)  
        if self.min_total_amount:
            # member.total_spent >= self.min_total_amount
            pass
            
        return True


class MemberGradeHistory(models.Model):
    """
    🎯 회원 등급 변경 이력 테이블
    - 등급 변경 내역 추적
    - 변경 사유 및 관리자 정보 기록
    """
    
    # 연결 정보
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name='grade_histories',
        verbose_name="회원"
    )
    
    # 등급 변경 정보
    old_grade = models.ForeignKey(
        MemberGrade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='old_grade_histories',
        verbose_name="이전 등급"
    )
    
    new_grade = models.ForeignKey(
        MemberGrade,
        on_delete=models.CASCADE,
        related_name='new_grade_histories',
        verbose_name="새 등급"
    )
    
    # 변경 사유
    CHANGE_REASON_CHOICES = [
        ('auto', '자동 승급'),
        ('manual', '수동 변경'),
        ('signup', '신규 가입'),
        ('promotion', '특별 승급'),
        ('demotion', '등급 강등'),
        ('fixed', '등급 고정'),
        ('unfixed', '고정 해제'),
    ]
    
    change_reason = models.CharField(
        max_length=20,
        choices=CHANGE_REASON_CHOICES,
        default='manual',
        verbose_name="변경 사유"
    )
    
    reason_detail = models.TextField(
        blank=True,
        verbose_name="상세 사유",
        help_text="등급 변경에 대한 상세한 설명"
    )
    
    # 변경자 정보
    changed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="변경자",
        help_text="관리자가 수동 변경한 경우"
    )
    
    # 시스템 필드
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="변경일시")
    
    class Meta:
        verbose_name = "등급 변경 이력"
        verbose_name_plural = "등급 변경 이력"
        ordering = ['-created_at']
    
    def __str__(self):
        old_name = self.old_grade.display_name if self.old_grade else "없음"
        return f"{self.member.name}: {old_name} → {self.new_grade.display_name}"


# 기존 Member 모델에 추가할 필드들
"""
Member 모델에 다음 필드들을 추가하세요:

    # 등급 관련 필드들 (Member 모델에 추가)
    grade = models.ForeignKey(
        MemberGrade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="회원 등급"
    )
    
    grade_fixed = models.BooleanField(
        default=False,
        verbose_name="등급 고정",
        help_text="체크 시 자동 승급/강등 방지"
    )
    
    grade_fixed_reason = models.TextField(
        blank=True,
        verbose_name="등급 고정 사유"
    )
    
    grade_fixed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fixed_grade_members',
        verbose_name="등급 고정한 관리자"
    )
    
    grade_fixed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="등급 고정 일시"
    )
"""