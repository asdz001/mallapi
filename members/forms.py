# members/forms.py
# ------------------------------------------------------------
# 수정된 부분: field_config.py를 활용한 동적 필드 생성
# UX 변경 없음: 기존과 동일한 화면과 동작 보장
# 오류 수정: Meta 클래스에서 self 사용 문제 해결
# ------------------------------------------------------------

from django import forms
from django.contrib.auth.hashers import make_password
from .models import Member
from .field_config import (
    MEMBER_FIELDS, 
    get_form_fields, 
    get_required_fields,
    FIELD_GROUPS
)

def _digits(s: str) -> str:
    """숫자만 추출하는 헬퍼 함수 (기존과 동일)"""
    return ''.join(ch for ch in (s or '') if ch.isdigit())

# ========================================
# 🛠️ 헬퍼 함수들 (클래스 외부에서 정의)
# ========================================

def _get_form_fields_list():
    """
    폼에서 사용할 필드 목록을 동적으로 생성
    기존 필드들을 모두 포함하여 UX 변경 없음 보장
    """
    # field_config.py에서 기본 필드들 가져오기
    config_fields = list(get_form_fields().keys())
    
    # ✅ 기존 필드들 명시적 추가 (UX 변경 없음)
    base_fields = [
        "username", "member_type", "name", "email", "phone",
        "address", "zip_code", "gender", "birth_date",
        "marketing_agree", "is_forever_member", "is_sms_agree",
        "recommender_id", "join_channel", "memo",
        # B2B 필드들
        "company_name", "business_number", "representative_name",
        "business_type", "business_item", "company_phone", 
        "fax", "company_address",
        # 시스템 필드
        "is_active",
    ]
    
    # 중복 제거 후 반환
    all_fields = list(dict.fromkeys(base_fields + config_fields))
    return all_fields

def _get_form_widgets():
    """
    폼 위젯을 동적으로 생성
    기존 위젯 설정을 모두 포함하여 UX 변경 없음
    """
    # ✅ 기존 위젯들 유지 (UX 변경 없음)
    base_widgets = {
        "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "아이디"}),
        "member_type": forms.Select(attrs={"class": "form-control"}),
        "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "이름"}),
        "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "example@domain.com"}),
        "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "010-0000-0000"}),
        "address": forms.TextInput(attrs={"class": "form-control", "placeholder": "주소", "readonly": "readonly"}),
        "zip_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "우편번호", "readonly": "readonly"}),
        "gender": forms.Select(attrs={"class": "form-control"}),
        "birth_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        "marketing_agree": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        "is_forever_member": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        "is_sms_agree": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        "recommender_id": forms.TextInput(attrs={"class": "form-control"}),
        "join_channel": forms.Select(attrs={"class": "form-control"}),
        "memo": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        # B2B 위젯들
        "company_name": forms.TextInput(attrs={"class": "form-control"}),
        "business_number": forms.TextInput(attrs={"class": "form-control"}),
        "representative_name": forms.TextInput(attrs={"class": "form-control"}),
        "business_type": forms.TextInput(attrs={"class": "form-control"}),
        "business_item": forms.TextInput(attrs={"class": "form-control"}),
        "company_phone": forms.TextInput(attrs={"class": "form-control"}),
        "fax": forms.TextInput(attrs={"class": "form-control"}),
        "company_address": forms.TextInput(attrs={"class": "form-control", "placeholder": "회사 주소"}),
        "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
    }
    
    # 🆕 field_config.py에서 추가 위젯 생성 (향후 확장용)
    config_widgets = {}
    try:
        form_fields = get_form_fields()
        
        for field_name, field_config in form_fields.items():
            if field_name not in base_widgets:  # 기존에 없는 필드만
                widget_attrs = {"class": "form-control"}
                
                field_type = field_config.get('type', 'text')
                if field_type == 'boolean':
                    widget_attrs["class"] = "form-check-input"
                elif field_type == 'textarea':
                    widget_attrs["rows"] = field_config.get('rows', 3)
                elif field_type == 'date':
                    widget_attrs["type"] = "date"
                elif field_type == 'email':
                    widget_attrs["placeholder"] = "example@domain.com"
                
                # 위젯 클래스 결정
                if field_type == 'boolean':
                    widget_class = forms.CheckboxInput
                elif field_type == 'choice':
                    widget_class = forms.Select
                elif field_type == 'textarea':
                    widget_class = forms.Textarea
                elif field_type == 'date':
                    widget_class = forms.DateInput
                elif field_type == 'email':
                    widget_class = forms.EmailInput
                else:
                    widget_class = forms.TextInput
                
                config_widgets[field_name] = widget_class(attrs=widget_attrs)
    except Exception as e:
        # field_config.py에 문제가 있어도 기존 기능은 작동하도록
        print(f"field_config.py 로딩 중 오류: {e}")
    
    # 기존 위젯 + 새로운 위젯 결합
    base_widgets.update(config_widgets)
    return base_widgets

class MemberCreateForm(forms.ModelForm):
    """
    회원 생성 폼 - field_config.py 기반으로 동적 생성
    기존 UX와 완전히 동일하게 작동
    """
    
    # 🆕 추가 커스텀 필드들 (기존 로직 유지)
    address_detail = forms.CharField(
        required=False, 
        label="상세주소",
        widget=forms.TextInput(attrs={
            "class": "form-control", 
            "placeholder": "상세주소"
        })
    )
    
    company_address_detail = forms.CharField(
        required=False, 
        label="회사 상세주소",
        widget=forms.TextInput(attrs={
            "class": "form-control", 
            "placeholder": "회사 상세주소"
        })
    )
    
    password1 = forms.CharField(
        label="비밀번호",
        widget=forms.PasswordInput(attrs={
            "class": "form-control", 
            "placeholder": "비밀번호(8자 이상)"
        })
    )
    
    password2 = forms.CharField(
        label="비밀번호 확인",
        widget=forms.PasswordInput(attrs={
            "class": "form-control", 
            "placeholder": "비밀번호 확인"
        })
    )

    class Meta:
        model = Member
        # 🔧 수정: 함수를 직접 호출 (self 사용하지 않음)
        fields = _get_form_fields_list()
        widgets = _get_form_widgets()
    
    def __init__(self, *args, **kwargs):
        """
        폼 초기화 - 기존 로직 유지
        """
        super().__init__(*args, **kwargs)
        
        # ✅ 기존 로직 유지 (UX 변경 없음)
        self.fields["join_channel"].required = False
        self.fields["join_channel"].initial = "direct"
        
        # 🆕 동적 필드 설정 (향후 확장용)
        self._setup_dynamic_field_properties()
    
    def _setup_dynamic_field_properties(self):
        """
        field_config.py 설정을 기반으로 필드 속성 설정
        기존 설정을 override하지 않고 보완만 함
        """
        try:
            form_fields = get_form_fields()
            
            for field_name, field_config in form_fields.items():
                if field_name in self.fields:
                    field = self.fields[field_name]
                    
                    # help_text 추가 (기존에 없는 경우만)
                    if field_config.get('help_text') and not field.help_text:
                        field.help_text = field_config['help_text']
                        
                    # 필수 여부 설정 (기존 설정 유지 우선)
                    if not hasattr(field, '_original_required'):
                        if field_config.get('required') == True:
                            field.required = True
                        elif field_config.get('required') == False:
                            field.required = False
        except Exception as e:
            # field_config.py에 문제가 있어도 폼은 정상 작동
            print(f"동적 필드 설정 중 오류: {e}")

    # ========================================
    # ✅ 기존 검증 로직 완전 유지 (UX 변경 없음)
    # ========================================
    
    def clean_email(self):
        """이메일 중복 검사 (기존 로직 유지)"""
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            return email
        if Member.objects.filter(email=email).exists():
            raise forms.ValidationError('이미 사용 중인 이메일입니다.')
        return email
    
    def clean(self):
        """전체 폼 검증 (기존 로직 완전 유지)"""
        cleaned = super().clean()

        # 🔐 기존 비밀번호 검사 (그대로 유지)
        pw1 = (cleaned.get("password1") or "").strip()
        pw2 = (cleaned.get("password2") or "").strip()
        if pw1 != pw2:
            self.add_error("password2", "비밀번호가 일치하지 않습니다.")
        if pw1 and len(pw1) < 8:
            self.add_error("password1", "비밀번호는 8자 이상이어야 합니다.")

        # 🧾 B2B일 때 '입력된 경우에만' 사업자번호 중복 검사 (기존 로직 유지)
        member_type = (cleaned.get("member_type") or "").strip()
        raw_bizno = cleaned.get("business_number") or ""
        if member_type == "B2B" and raw_bizno:
            biz = _digits(raw_bizno)  # '123-45-67890' → '1234567890'
            if Member.objects.filter(business_number=biz).exists():
                self.add_error("business_number", "이미 등록된 사업자번호입니다.")
            else:
                self.cleaned_data["business_number"] = biz

        return cleaned
    
    def clean_join_channel(self):
        """가입채널 검증 (기존 로직 유지)"""
        v = (self.cleaned_data.get("join_channel") or "").strip()
        return v or "direct"

    def save(self, commit=True):
        """저장 로직 (기존 로직 완전 유지)"""
        instance = super().save(commit=False)

        # ✅ 기존 비밀번호 처리 로직 유지
        raw_password = self.cleaned_data.get("password1")
        if raw_password:
            instance.password = make_password(raw_password)

        # ✅ 기존 주소 합치기 로직 유지
        base_addr = (self.cleaned_data.get("address") or "").strip()
        detail = (self.cleaned_data.get("address_detail") or "").strip()
        instance.address = f"{base_addr} {detail}".strip() if detail else base_addr

        # ✅ 기존 회사주소 합치기 로직 유지
        base_caddr = (self.cleaned_data.get("company_address") or "").strip()
        cdetail = (self.cleaned_data.get("company_address_detail") or "").strip()
        instance.company_address = f"{base_caddr} {cdetail}".strip() if cdetail else base_caddr

        # ✅ 기존 기본값 보정 로직 유지
        if not instance.join_channel:
            instance.join_channel = "direct"

        if commit:
            instance.save()
        return instance
    

class MemberUpdateForm(forms.ModelForm):
    """
    회원 수정 폼 - MemberCreateForm 기반으로 수정용 최적화
    기존 데이터 수정에 특화된 폼
    """
    
    class Meta:
        model = Member
        # 수정 가능한 필드만 포함 (username, password 제외)
        fields = [
            'name', 'email', 'phone', 'address', 'zip_code', 'is_active',
            'gender', 'birth_date', 'marketing_agree', 'is_sms_agree', 
            'recommender_id', 'join_channel', 'memo', 'nickname',
            # B2B 필드들
            'company_name', 'business_number', 'representative_name',
            'business_type', 'business_item', 'company_phone', 
            'fax', 'company_address', 'is_forever_member', 'is_blacklisted'
        ]
        
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "zip_code": forms.TextInput(attrs={"class": "form-control"}),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "birth_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "marketing_agree": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_sms_agree": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "recommender_id": forms.TextInput(attrs={"class": "form-control"}),
            "join_channel": forms.Select(attrs={"class": "form-control"}),
            "memo": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "nickname": forms.TextInput(attrs={"class": "form-control"}),
            # B2B 위젯들
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "business_number": forms.TextInput(attrs={"class": "form-control"}),
            "representative_name": forms.TextInput(attrs={"class": "form-control"}),
            "business_type": forms.TextInput(attrs={"class": "form-control"}),
            "business_item": forms.TextInput(attrs={"class": "form-control"}),
            "company_phone": forms.TextInput(attrs={"class": "form-control"}),
            "fax": forms.TextInput(attrs={"class": "form-control"}),
            "company_address": forms.TextInput(attrs={"class": "form-control"}),
            "is_forever_member": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_blacklisted": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
    
    def __init__(self, *args, **kwargs):
        """폼 초기화 - 수정용 특별 설정"""
        super().__init__(*args, **kwargs)
        
        # 선택적 필드 설정
        self.fields["join_channel"].required = False
        self.fields["email"].required = False
        
        # member_type에 따라 필드 조건 설정
        if self.instance and self.instance.member_type == 'B2B':
            self.fields["company_name"].required = False  # 수정 시에는 필수 아님
            self.fields["business_number"].required = False
    
    def clean_email(self):
        """이메일 중복 검사 (현재 회원 제외)"""
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            return email
            
        # 현재 수정 중인 회원은 중복 검사에서 제외
        existing = Member.objects.filter(email=email)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
            
        if existing.exists():
            raise forms.ValidationError('이미 사용 중인 이메일입니다.')
        return email
    
    def clean_business_number(self):
        """사업자번호 중복 검사 (현재 회원 제외)"""
        bizno = self.cleaned_data.get('business_number')
        if not bizno:
            return bizno
            
        biz = _digits(bizno)  # 숫자만 추출
        if not biz:
            return bizno
            
        # 현재 수정 중인 회원은 중복 검사에서 제외
        existing = Member.objects.filter(business_number=biz)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
            
        if existing.exists():
            raise forms.ValidationError('이미 등록된 사업자번호입니다.')
        return biz
    
    def clean_join_channel(self):
        """가입채널 검증"""
        v = (self.cleaned_data.get("join_channel") or "").strip()
        return v or "direct"