# mall_settings/forms.py
from django import forms
from .models import SiteSetting
from ckeditor.widgets import CKEditorWidget
from django.contrib.auth.models import User
from mall_settings.models import OperatorProfile
from pricing.models import Retailer

# 쇼핑몰 설정 폼
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
            'privacy_policy': CKEditorWidget(),
            'ecommerce_notice': CKEditorWidget(),
            'return_policy': CKEditorWidget(),
        }





# 운영자 프로필 폼
class OperatorForm(forms.ModelForm):
    # 장고 유저 필드
    username = forms.CharField(label="아이디", max_length=150)
    email = forms.EmailField(label="이메일")
    first_name = forms.CharField(label="이름", max_length=30)
    password = forms.CharField(label="비밀번호", widget=forms.PasswordInput, required=False)
    confirm_password = forms.CharField(label='비밀번호 확인',required=False, widget=forms.PasswordInput()) # 비워도 폼 검증 통과 가능하게

    # OperatorProfile 필드
    contact_number = forms.CharField(label="연락처", max_length=20, required=False)
    allowed_retailers = forms.ModelMultipleChoiceField(
        label="접근 거래처",
        queryset=Retailer.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    receive_order_alerts = forms.BooleanField(label="주문 알림", required=False)
    receive_stock_alerts = forms.BooleanField(label="재고 알림", required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'password']

    # 생성자에서 유저 인스턴스 받아오기
    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)  # 수정할 유저 인스턴스 받아오기
        super().__init__(*args, **kwargs)

    
    # 폼 검증
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        # 둘 다 있을 경우 비교
        if password or confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("비밀번호와 비밀번호 확인이 일치하지 않습니다.")

        return cleaned_data
        
    # 저장 메소드
    def save(self, commit=True, user_instance=None):
        if user_instance:
            user = user_instance
            user.username = self.cleaned_data['username']
            user.email = self.cleaned_data['email']
            user.first_name = self.cleaned_data['first_name']
            if self.cleaned_data['password']:
                user.set_password(self.cleaned_data['password'])
        else:
            user = User(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                first_name=self.cleaned_data['first_name'],
            )
            if self.cleaned_data['password']:
                user.set_password(self.cleaned_data['password'])

        if commit:
            user.save()

            # OperatorProfile 저장
            profile, created = OperatorProfile.objects.get_or_create(user=user)
            profile.contact_number = self.cleaned_data['contact_number']
            profile.receive_order_alerts = self.cleaned_data['receive_order_alerts']
            profile.receive_stock_alerts = self.cleaned_data['receive_stock_alerts']
            if commit:
                profile.save()
                profile.allowed_retailers.set(self.cleaned_data['allowed_retailers'])

        return user
