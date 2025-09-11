# promotion/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Coupon, Event, PromotionRule
from members.models import MemberGrade
import re

class CouponForm(forms.ModelForm):
    """
    쿠폰 생성/수정 폼
    - 정액/정률 할인 설정
    - 사용 조건 및 제한 설정
    """

    # 커스텀 필드 추가
    auto_generate_code = forms.BooleanField(
        required=False,
        initial=False,
        label="자동 코드 생성",
        help_text="체크 시 랜덤 코드 자동 생성"
    )

    class Meta:
        model = Coupon
        fields = [
            'name', 'code', 'auto_generate_code', 'description',
            'discount_type', 'discount_value', 'max_discount_amount',
            'min_purchase_amount', 'usage_limit', 'usage_limit_per_user',
            'start_date', 'end_date', 'target_member_types', 'target_grades',
            'is_active'
        ]

        widgets = {
            # 기본 정보
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '쿠폰명을 입력하세요'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '쿠폰 코드 (영문 대문자, 숫자 조합)',
                'style': 'text-transform: uppercase;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '쿠폰에 대한 설명을 입력하세요'
            }),

            # 할인 설정
            'discount_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_discount_type'  # JS에서 사용
            }),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '할인 값을 입력하세요',
                'step': '0.01'
            }),
            'max_discount_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '정률할인 시 최대 할인금액 (선택사항)'
            }),

            # 사용 조건
            'min_purchase_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '최소 구매금액 (0원부터)',
                'min': '0'
            }),
            'usage_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '전체 사용 제한 (미입력시 무제한)',
                'min': '1'
            }),
            'usage_limit_per_user': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '회원별 사용 제한',
                'min': '1',
                'value': '1'
            }),

            # 기간 설정
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),

            # 대상 설정
            'target_member_types': forms.Select(attrs={
                'class': 'form-control'
            }),
            'target_grades': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '5'
            }),

            # 상태
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 등급 선택 필드 동적 구성
        self.fields['target_grades'].queryset = MemberGrade.objects.filter(
            is_active=True
        ).order_by('member_type', 'order')

        # 등급 선택 필드 레이블 커스터마이징
        choices = []
        for grade in self.fields['target_grades'].queryset:
            label = f"[{grade.member_type}] {grade.display_name}"
            choices.append((grade.id, label))
        self.fields['target_grades'].choices = choices

        # 필드별 도움말 설정
        self.fields['target_grades'].help_text = "미선택시 모든 등급 적용 가능"
        self.fields['max_discount_amount'].help_text = "정률할인 시에만 적용됩니다"

        # ✅ [핵심] code는 서버 단에서는 '선택'으로 두고,
        #    clean_code()/clean()에서 자동생성 여부로 최종 판단
        self.fields['code'].required = False

    def _auto_generate_checked(self) -> bool:
        """
        ✅ 자동생성 체크 여부를 '안전하게' 판단
        - cleaned_data에 값이 없을 수 있는 타이밍을 대비해 self.data까지 확인
        - Django 체크박스는 보통 'on'으로 넘어옴
        """
        from_post = str(self.data.get('auto_generate_code', '')).strip().lower()
        return bool(
            self.cleaned_data.get('auto_generate_code') or
            from_post in ('on', 'true', '1', 'yes')
        )

    def clean_code(self):
        """쿠폰 코드 검증 - 자동생성/수동입력 모두 지원"""
        code = (self.cleaned_data.get('code') or '').strip()

        # ✅ 변경: 자동생성 체크를 self.data까지 확인해서 필드 타이밍 이슈 제거
        if self._auto_generate_checked():
            return Coupon.generate_code()

        # 자동생성이 아닌 경우에만 코드 검증
        if not code:
            raise ValidationError("쿠폰 코드를 입력하거나 자동 생성을 선택하세요.")

        # 형식 검증
        if not re.match(r'^[A-Z0-9]+$', code):
            raise ValidationError("쿠폰 코드는 영문 대문자와 숫자만 사용 가능합니다.")

        if len(code) < 4 or len(code) > 20:
            raise ValidationError("쿠폰 코드는 4-20자 사이여야 합니다.")

        # 중복 검증
        existing = Coupon.objects.filter(code=code.upper())
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError("이미 존재하는 쿠폰 코드입니다.")

        return code.upper()

    def clean(self):
        """전체 폼 검증"""
        cleaned_data = super().clean()
        discount_type = cleaned_data.get('discount_type')
        discount_value = cleaned_data.get('discount_value')
        max_discount_amount = cleaned_data.get('max_discount_amount')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        # ✅ 최종 안전망: 자동생성인데 code가 여전히 비어있으면 여기서 생성
        if self._auto_generate_checked() and not cleaned_data.get('code'):
            cleaned_data['code'] = Coupon.generate_code()

        # 할인 값 검증
        if discount_value is not None:
            if discount_type == 'percent' and discount_value > 100:
                raise ValidationError("정률할인은 100%를 초과할 수 없습니다.")
            elif discount_value <= 0:
                raise ValidationError("할인 값은 0보다 커야 합니다.")

        # 정률할인 시 최대 할인금액 검증
        if discount_type == 'percent' and max_discount_amount and max_discount_amount <= 0:
            raise ValidationError("최대 할인금액은 0보다 커야 합니다.")

        # 기간 검증
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError("종료일시는 시작일시보다 늦어야 합니다.")
            # 과거 시간 체크 (새 쿠폰만)
            if not self.instance.pk and start_date < timezone.now():
                raise ValidationError("시작일시는 현재 시간 이후여야 합니다.")

        return cleaned_data


class EventForm(forms.ModelForm):
    """
    이벤트 할인 생성/수정 폼
    - 기간별 전체/카테고리 할인 설정
    """

    class Meta:
        model = Event
        fields = [
            'name', 'description', 'discount_type', 'discount_value',
            'max_discount_amount', 'target_all_products', 'target_categories',
            'target_brands', 'start_date', 'end_date', 'min_purchase_amount',
            'priority', 'is_active'
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '이벤트명을 입력하세요'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '이벤트에 대한 설명을 입력하세요'
            }),
            'discount_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_event_discount_type'
            }),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'max_discount_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '정률할인 시 최대 할인금액 (선택사항)'
            }),
            'target_all_products': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_target_all_products'
            }),
            'target_categories': forms.HiddenInput(),

            'target_brands': forms.HiddenInput(),
            
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'min_purchase_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'priority': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '100'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean(self):
        """전체 폼 검증"""
        cleaned_data = super().clean()
        discount_type = cleaned_data.get('discount_type')
        discount_value = cleaned_data.get('discount_value')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        target_all_products = cleaned_data.get('target_all_products')
        target_categories = cleaned_data.get('target_categories')
        target_brands = cleaned_data.get('target_brands')

        # 할인 값 검증
        if discount_value is not None:
            if discount_type == 'percent' and discount_value > 100:
                raise ValidationError("정률할인은 100%를 초과할 수 없습니다.")
            elif discount_value <= 0:
                raise ValidationError("할인 값은 0보다 커야 합니다.")

        # 기간 검증
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError("종료일시는 시작일시보다 늦어야 합니다.")

        # 대상 상품 검증
        if not target_all_products:
            if not target_categories and not target_brands:
                raise ValidationError(
                    "전체 상품 적용을 해제한 경우, 대상 카테고리나 브랜드를 지정해야 합니다."
                )

        return cleaned_data


class PromotionRuleForm(forms.ModelForm):
    """
    프로모션 규칙 설정 폼
    - 할인 우선순위 및 중복허용 규칙
    """

    class Meta:
        model = PromotionRule
        fields = [
            'name', 'priority_order', 'allow_coupon_stack',
            'allow_grade_coupon_stack', 'max_discount_rate', 'is_active'
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '규칙명을 입력하세요'
            }),
            'priority_order': forms.Select(attrs={
                'class': 'form-control'
            }),
            'allow_coupon_stack': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'allow_grade_coupon_stack': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'max_discount_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class CouponBulkCreateForm(forms.Form):
    """
    쿠폰 대량 생성 폼
    - 동일한 조건의 쿠폰 여러 개 생성
    """

    # 기본 정보
    base_name = forms.CharField(
        max_length=100,
        label="기본 쿠폰명",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '예: 신규회원 할인 쿠폰'
        }),
        help_text="생성되는 쿠폰들의 기본 이름"
    )

    quantity = forms.IntegerField(
        min_value=1,
        max_value=1000,
        label="생성 개수",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '생성할 쿠폰 개수 (최대 1000개)'
        })
    )

    code_prefix = forms.CharField(
        max_length=10,
        required=False,
        label="코드 접두사",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '예: WELCOME (선택사항)'
        }),
        help_text="쿠폰 코드 앞에 붙을 문자 (미입력시 랜덤 생성)"
    )

    # 할인 설정
    discount_type = forms.ChoiceField(
        choices=Coupon.DISCOUNT_TYPE_CHOICES,
        label="할인 타입",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    discount_value = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        label="할인 값",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )

    # 기간 설정
    start_date = forms.DateTimeField(
        label="시작일시",
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )

    end_date = forms.DateTimeField(
        label="종료일시",
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date >= end_date:
            raise ValidationError("종료일시는 시작일시보다 늦어야 합니다.")

        return cleaned_data


class CouponSearchForm(forms.Form):
    """
    쿠폰 검색/필터 폼
    """

    search = forms.CharField(
        required=False,
        label="검색",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '쿠폰명 또는 코드로 검색'
        })
    )

    discount_type = forms.ChoiceField(
        required=False,
        choices=[('', '모든 할인타입')] + list(Coupon.DISCOUNT_TYPE_CHOICES),
        label="할인 타입",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', '모든 상태'),
            ('active', '활성화'),
            ('inactive', '비활성화'),
            ('expired', '만료됨'),
        ],
        label="상태",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    target_member_type = forms.ChoiceField(
        required=False,
        choices=[('', '모든 회원타입'), ('B2C', 'B2C 회원'), ('B2B', 'B2B 회원')],
        label="대상 회원",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
