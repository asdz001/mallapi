# mall_settings/forms.py
# ------------------------------------------------------------
# 1) 쇼핑몰 기본 설정 폼(SiteSettingForm) - 기존 코드 유지
# 2) 운영자 폼(OperatorForm) - 비번 안전가드/프로필 저장 보강
#    - 수정 시 비번 비워두면 '미변경'
#    - 둘 중 하나만 입력하면 에러
#    - 둘 다 입력되면 일치해야 통과
#    - 프로필(OperatorProfile) 저장 + allowed_retailers(M2M) 안전 저장
# ------------------------------------------------------------

from django import forms
from ckeditor.widgets import CKEditorWidget
from django.contrib.auth.models import User

from .models import SiteSetting
from mall_settings.models import OperatorProfile
from pricing.models import Retailer


# ---------------------------
# 1) 쇼핑몰 설정 폼 (기존 유지)
# ---------------------------
class SiteSettingForm(forms.ModelForm):
    class Meta:
        model = SiteSetting
        fields = '__all__'
        widgets = {
            'site_name': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'business_hours': forms.TextInput(attrs={'class': 'form-control'}),
            'ceo_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_number': forms.TextInput(attrs={'class': 'form-control'}),
            'commerce_number': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.TextInput(attrs={'class': 'form-control'}),
            'business_license_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'footer_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'terms_of_service': CKEditorWidget(),
            # 필요에 따라 추가 위젯을 여기서 계속 확장
        }


# ---------------------------------------------
# 2) 운영자 생성/수정 폼 (안전가드/주석 강화 버전)
# ---------------------------------------------
class OperatorForm(forms.ModelForm):
    """
    운영자 생성/수정에 사용하는 폼.
    - 핵심 유저 정보(User): username, email, first_name
    - 비밀번호/비밀번호확인:
        * 수정 시 비워두면 '미변경'
        * 둘 중 하나만 입력되면 에러
        * 둘 다 입력되면 일치해야 통과
    - 프로필(OperatorProfile) 필드: contact_number, receive_*_alerts, allowed_retailers
    """
    # ✅ 장고 User 필드
    username = forms.CharField(label="아이디", max_length=150)
    email = forms.EmailField(label="이메일", required=True)
    first_name = forms.CharField(label="이름", max_length=30, required=True)

    # ✅ 비밀번호 입력(수정 시 선택)
    password = forms.CharField(
        label="비밀번호",
        widget=forms.PasswordInput,
        required=False,  # 수정 시 비워두면 '미변경'
        help_text="수정 시 비워두면 기존 비밀번호가 유지됩니다.",
    )
    confirm_password = forms.CharField(
        label="비밀번호 확인",
        widget=forms.PasswordInput,
        required=False,
        help_text="비밀번호 변경 시에만 입력하세요.",
    )

    # ✅ OperatorProfile 필드
    contact_number = forms.CharField(label="연락처", max_length=20, required=False)
    receive_order_alerts = forms.BooleanField(label="주문 알림 수신", required=False)
    receive_stock_alerts = forms.BooleanField(label="재고 알림 수신", required=False)
    allowed_retailers = forms.ModelMultipleChoiceField(
        label="접근 가능한 거래처",
        queryset=Retailer.objects.all(),
        required=False,
        # 체크박스/멀티셀렉트 등 프로젝트 UI에 맞춰 교체 가능
        widget=forms.SelectMultiple(attrs={"class": "form-control"})
    )

    class Meta:
        # 바인딩 모델은 User. ⚠️ 모델 필드만 넣는다. (password는 모델에 직접 쓰지 않게 제외)
        model = User
        fields = ("username", "email", "first_name")

    def __init__(self, *args, **kwargs):
        # update 시 user_instance를 넘겨받아 필드 초기화/검증에 활용
        self.user_instance = kwargs.pop("user_instance", None)
        super().__init__(*args, **kwargs)

        # 공통 UI 클래스 부여(부트스트랩). 체크박스는 form-control 미적용.
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                existing = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = (existing + " form-control").strip()

    # ✅ 비밀번호 검증
    def clean(self):
        """
        - 둘 중 하나만 입력 → 에러
        - 둘 다 입력 → 일치해야 함
        - 둘 다 빈칸 → 수정 시 비밀번호 미변경(통과)
        """
        cleaned = super().clean()
        # 공백만 입력된 경우는 빈값으로 정규화 → '미변경' 처리
        pwd = (cleaned.get("password") or "").strip()
        pwd2 = (cleaned.get("confirm_password") or "").strip()
        cleaned["password"] = pwd
        cleaned["confirm_password"] = pwd2

        if (pwd and not pwd2) or (pwd2 and not pwd):
            raise forms.ValidationError("비밀번호와 비밀번호 확인을 모두 입력해주세요.")

        if pwd and pwd2 and (pwd != pwd2):
            raise forms.ValidationError("비밀번호와 비밀번호 확인이 일치하지 않습니다.")

        return cleaned

    # ✅ 저장 로직(User + OperatorProfile + allowed_retailers)
    def save(self, commit=True, user_instance=None):
        """
        - user_instance가 있으면 업데이트, 없으면 생성
        - 비밀번호는 '입력 시에만' set_password()
        - 프로필(OperatorProfile) 저장 + allowed_retailers set()
        """
        user = user_instance or User()

        # 기본 정보 반영
        user.username = self.cleaned_data["username"]
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]

        # 비밀번호는 '입력된 경우에만' 변경
        pwd = self.cleaned_data.get("password")
        if pwd:
            user.set_password(pwd)

        if commit:
            user.save()

            # 프로필 저장
            profile, _ = OperatorProfile.objects.get_or_create(user=user)
            profile.contact_number = self.cleaned_data.get("contact_number")
            profile.receive_order_alerts = self.cleaned_data.get("receive_order_alerts") or False
            profile.receive_stock_alerts = self.cleaned_data.get("receive_stock_alerts") or False
            profile.save()

            # M2M은 프로필 저장 후 set()
            allowed = self.cleaned_data.get("allowed_retailers")
            if allowed is not None:
                profile.allowed_retailers.set(allowed)

        return user
