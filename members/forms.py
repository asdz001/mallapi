from django import forms
from django.contrib.auth.hashers import make_password
from .models import Member  # 경로 확인


def _digits(s: str) -> str:
    return ''.join(ch for ch in (s or '') if ch.isdigit())

class MemberCreateForm(forms.ModelForm):
    # 상세주소(개인)
    address_detail = forms.CharField(
        required=False, label="상세주소",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "상세주소"})
    )
    # 상세주소(B2B)
    company_address_detail = forms.CharField(
        required=False, label="회사 상세주소",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "회사 상세주소"})
    )

    password1 = forms.CharField(
        label="비밀번호",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "비밀번호(8자 이상)"})
    )
    password2 = forms.CharField(
        label="비밀번호 확인",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "비밀번호 확인"})
    )

    class Meta:
        model = Member
        fields = [
            "username", "member_type", "name",
            "email", "phone",
            "address", "zip_code",          # 기본주소/우편번호
            "gender", "birth_date",
            "marketing_agree", "is_forever_member", "is_sms_agree",
            "recommender_id", "join_channel", "memo",
            # B2B
            "company_name", "business_number", "representative_name",
            "business_type", "business_item", "company_phone", "fax", "company_address",
            # 상태
            "is_active",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "아이디"}),
            "member_type": forms.Select(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "이름"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "example@domain.com"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "010-0000-0000"}),
            "address":  forms.TextInput(attrs={"class": "form-control", "placeholder": "주소", "readonly": "readonly"}),
            "zip_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "우편번호", "readonly": "readonly"}),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "birth_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "marketing_agree": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_forever_member": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_sms_agree": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "recommender_id": forms.TextInput(attrs={"class": "form-control"}),
            "join_channel": forms.Select(attrs={"class": "form-control"}),
            "memo": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            # B2B
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


    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            return email  # 이메일은 필수가 아니므로 미입력은 그대로 통과
        # 같은 이메일이 이미 존재하면 막기
        if Member.objects.filter(email=email).exists():
            raise forms.ValidationError('이미 사용 중인 이메일입니다.')
        return email
            

    def clean(self):
        cleaned = super().clean()

        # 🔐 기존 비밀번호 검사 (그대로 유지)
        pw1 = (cleaned.get("password1") or "").strip()
        pw2 = (cleaned.get("password2") or "").strip()
        if pw1 != pw2:
            self.add_error("password2", "비밀번호가 일치하지 않습니다.")
        if pw1 and len(pw1) < 8:
            self.add_error("password1", "비밀번호는 8자 이상이어야 합니다.")

        # 🧾 B2B일 때 '입력된 경우에만' 사업자번호 중복 검사 (+정규화 저장)
        member_type = (cleaned.get("member_type") or "").strip()
        raw_bizno   = cleaned.get("business_number") or ""
        if member_type == "B2B" and raw_bizno:
            biz = _digits(raw_bizno)  # '123-45-67890' → '1234567890'
            # 숫자만 기준으로 중복 판단
            if Member.objects.filter(business_number=biz).exists():
                self.add_error("business_number", "이미 등록된 사업자번호입니다.")
            else:
                # 저장 일관성을 위해 정규화된 값으로 덮어쓰기
                self.cleaned_data["business_number"] = biz

        return cleaned
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ 가입채널 미선택 시에도 통과되도록
        self.fields["join_channel"].required = False   # 폼 유효성에서 필수 해제
        self.fields["join_channel"].initial = "direct" # 기본 노출값

    def clean_join_channel(self):
        # ✅ 값이 비어 있으면 "direct"로 보정
        v = (self.cleaned_data.get("join_channel") or "").strip()
        return v or "direct"


    def save(self, commit=True):
        """비밀번호 해시 + 주소/회사주소 상세 합치기"""
        instance = super().save(commit=False)

        # 비밀번호
        raw_password = self.cleaned_data.get("password1")
        if raw_password:
            instance.password = make_password(raw_password)

        # 개인 주소 합치기
        base_addr = (self.cleaned_data.get("address") or "").strip()
        detail    = (self.cleaned_data.get("address_detail") or "").strip()
        instance.address = f"{base_addr} {detail}".strip() if detail else base_addr

        # 회사 주소 합치기
        base_caddr = (self.cleaned_data.get("company_address") or "").strip()
        cdetail    = (self.cleaned_data.get("company_address_detail") or "").strip()
        instance.company_address = f"{base_caddr} {cdetail}".strip() if cdetail else base_caddr

        # 기본값 보정
        if not instance.join_channel:
            instance.join_channel = "direct"

            

        if commit:
            instance.save()
        return instance
