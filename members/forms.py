# members/forms.py
# ------------------------------------------------------------
# field_config 기반 동적 폼 구성 - 등급 선택 필드 강화
# ------------------------------------------------------------
from django import forms
from django.contrib.auth.hashers import make_password
from django.db import models
from .models import Member, MemberGrade  # ✅ MemberGrade 추가 import
from .field_config import (
    MEMBER_FIELDS,
    get_form_fields,
    get_required_fields,   # ← 필수필드 계산(회원유형 필요)
    FIELD_GROUPS,
)

# ─────────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────────
def _digits(text: str) -> str:
    """문자열에서 숫자만 추출"""
    return ''.join(ch for ch in (text or '') if ch.isdigit())


# ─────────────────────────────────────────────────────────────
# form.Meta: fields / widgets 구성 헬퍼
# ─────────────────────────────────────────────────────────────
def _get_form_fields_list():
    """
    form.Meta.fields 값을 구성한다.
    - 기존 화면 UX를 유지하기 위해 기본 필드 + field_config 정의 필드를 합쳐서 사용
    """
    base_fields = [
        # 기본 정보
        "username", "member_type", "name", "email", "phone",
        "address", "zip_code",
        # B2C
        "gender", "birth_date", "marketing_agree", "is_sms_agree",
        "recommender_id", "join_channel", "memo", "is_forever_member",
        # B2B
        "company_name", "business_number", "representative_name",
        "business_type", "business_item", "company_phone", "fax",
        "company_address",
        # 시스템
        "is_active",
        # 등급(필드 설정에 존재하면 표시됨)
        "grade", "grade_fixed", "grade_fixed_reason",
    ]

    try:
        cfg_fields = list(get_form_fields().keys())
    except Exception:
        cfg_fields = []

    # 중복 제거하여 반환
    all_fields = list(dict.fromkeys(base_fields + cfg_fields))
    return all_fields


def _get_form_widgets():
    """
    폼 위젯을 동적으로 구성한다.
    """
    base_widgets = {
        # 기본 정보
        "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "영문/숫자 조합"}),
        "member_type": forms.Select(attrs={"class": "form-control"}),
        "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "실명"}),
        "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "example@domain.com"}),
        "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "010-0000-0000"}),
        "address": forms.TextInput(attrs={"class": "form-control"}),
        "zip_code": forms.TextInput(attrs={"class": "form-control"}),
        # B2C
        "gender": forms.Select(attrs={"class": "form-control"}),
        "birth_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        "marketing_agree": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        "is_sms_agree": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        "recommender_id": forms.TextInput(attrs={"class": "form-control"}),
        "join_channel": forms.Select(attrs={"class": "form-control"}),
        "memo": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        "is_forever_member": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        # B2B
        "company_name": forms.TextInput(attrs={"class": "form-control"}),
        "business_number": forms.TextInput(attrs={"class": "form-control"}),
        "representative_name": forms.TextInput(attrs={"class": "form-control"}),
        "business_type": forms.TextInput(attrs={"class": "form-control"}),
        "business_item": forms.TextInput(attrs={"class": "form-control"}),
        "company_phone": forms.TextInput(attrs={"class": "form-control"}),
        "fax": forms.TextInput(attrs={"class": "form-control"}),
        "company_address": forms.TextInput(attrs={"class": "form-control"}),
        # 시스템
        "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        # ✅ 등급 관련 위젯 강화
        "grade": forms.Select(attrs={"class": "form-control", "id": "id_grade"}),  # JS에서 접근용 ID
        "grade_fixed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        "grade_fixed_reason": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    }

    # field_config 기반 추가 위젯
    config_widgets = {}
    try:
        form_fields = get_form_fields()
        for field_name, field_cfg in form_fields.items():
            if field_name in base_widgets:
                continue

            field_type = field_cfg.get("type", "text")
            attrs = {"class": "form-control"}

            if field_type == "boolean":
                widget_cls = forms.CheckboxInput
                attrs = {"class": "form-check-input"}
            elif field_type in ("choice", "choice_foreign"):   # ✅ 수정: FK 선택도 Select로
                widget_cls = forms.Select
            elif field_type == "choice_multiple":
                widget_cls = forms.SelectMultiple
            elif field_type == "textarea":
                widget_cls = forms.Textarea
                attrs["rows"] = field_cfg.get("rows", 3)
            elif field_type == "date":
                widget_cls = forms.DateInput
                attrs["type"] = "date"
            elif field_type == "email":
                widget_cls = forms.EmailInput
                attrs["placeholder"] = "example@domain.com"
            else:
                widget_cls = forms.TextInput

            config_widgets[field_name] = widget_cls(attrs=attrs)
    except Exception as e:
        # 설정 오류가 있어도 폼은 렌더되도록 방어
        print(f"[forms] 동적 위젯 생성 오류: {e}")

    base_widgets.update(config_widgets)
    return base_widgets


# ─────────────────────────────────────────────────────────────
# 생성 폼
# ─────────────────────────────────────────────────────────────
class MemberCreateForm(forms.ModelForm):
    # 추가 커스텀 필드(상세주소 등)
    address_detail = forms.CharField(
        required=False,
        label="상세주소",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "상세주소"}),
    )
    company_address_detail = forms.CharField(
        required=False,
        label="회사 상세주소",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "회사 상세주소"}),
    )
    password1 = forms.CharField(
        label="비밀번호",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "비밀번호(8자 이상)"}),
    )
    password2 = forms.CharField(
        label="비밀번호 확인",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "비밀번호 확인"}),
    )

    class Meta:
        model = Member
        fields = _get_form_fields_list()
        widgets = _get_form_widgets()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ 회원 타입을 안전하게 추출
        member_type = None
        try:
            if self.data:
                member_type = (self.data.get("member_type") or "").strip()
            elif self.initial:
                member_type = (self.initial.get("member_type") or "").strip()
            elif hasattr(self, "instance") and self.instance and hasattr(self.instance, "member_type"):
                member_type = getattr(self.instance, "member_type", "").strip()
        except Exception:
            pass

        # ✅ 등급 선택 필드 동적 구성
        self._setup_grade_field(member_type)

        # 필수 필드 설정
        if member_type:
            try:
                required_fields = get_required_fields(member_type)
                for field_name in required_fields:
                    if field_name in self.fields:
                        self.fields[field_name].required = True
            except Exception:
                pass

        # 회원 타입별 필드 표시/숨김
        self._configure_fields_by_member_type(member_type)

    def _setup_grade_field(self, member_type):
        """등급 선택 필드 동적 구성"""
        if 'grade' in self.fields:
            try:
                # 기본 선택지: 빈 옵션
                choices = [('', '(자동) 기본 등급')]
                
                if member_type:
                    # 해당 회원타입에 맞는 등급들 조회
                    grades = MemberGrade.objects.filter(
                        models.Q(member_type=member_type) | models.Q(member_type='ALL'),
                        is_active=True
                    ).order_by('order', 'name')
                    
                    for grade in grades:
                        label = f"[{grade.member_type}] {grade.display_name or grade.name}"
                        if grade.is_default:
                            label += " (기본)"
                        choices.append((grade.id, label))
                else:
                    # 회원타입이 없으면 전체 등급 표시
                    grades = MemberGrade.objects.filter(is_active=True).order_by('member_type', 'order', 'name')
                    for grade in grades:
                        label = f"[{grade.member_type}] {grade.display_name or grade.name}"
                        if grade.is_default:
                            label += " (기본)"
                        choices.append((grade.id, label))
                
                self.fields['grade'].choices = choices
                
                # 도움말 텍스트 설정
                self.fields['grade'].help_text = "미선택 시 회원유형에 맞는 기본 등급이 자동 지정됩니다."
                
            except Exception as e:
                print(f"[forms] 등급 필드 설정 오류: {e}")
                # 오류 시 기본 선택지만 제공
                self.fields['grade'].choices = [('', '(자동) 기본 등급')]

    def _configure_fields_by_member_type(self, member_type):
        """회원 타입별 필드 표시/숨김 설정"""
        try:
            # B2C 전용 필드들
            b2c_fields = ['gender', 'birth_date', 'nickname', 'recommender_id', 
                         'join_channel', 'is_forever_member']
            
            # B2B 전용 필드들  
            b2b_fields = ['company_name', 'business_number', 'representative_name',
                         'business_type', 'business_item', 'company_phone', 'fax', 'company_address']
            
            if member_type == 'B2C':
                # B2B 필드들 비활성화
                for field in b2b_fields:
                    if field in self.fields:
                        self.fields[field].required = False
                        self.fields[field].widget.attrs['disabled'] = True
                        
            elif member_type == 'B2B':
                # B2C 필드들 비활성화
                for field in b2c_fields:
                    if field in self.fields:
                        self.fields[field].required = False
                        self.fields[field].widget.attrs['disabled'] = True
                        
        except Exception as e:
            print(f"[forms] 필드 구성 오류: {e}")

    def clean_password2(self):
        """비밀번호 확인 검증"""
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("비밀번호가 일치하지 않습니다.")
            
        return password2

    def clean_phone(self):
        """휴대폰 번호 검증 및 정규화"""
        phone = self.cleaned_data.get("phone", "")
        if phone:
            # 숫자만 추출
            digits = _digits(phone)
            if digits and len(digits) >= 10:
                # 하이픈 추가
                if len(digits) == 11:
                    return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
                elif len(digits) == 10:
                    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        return phone

    def clean_business_number(self):
        """사업자번호 검증 (B2B인 경우)"""
        business_number = self.cleaned_data.get("business_number", "")
        member_type = self.cleaned_data.get("member_type", "")
        
        if member_type == "B2B" and not business_number:
            raise forms.ValidationError("사업자회원은 사업자번호가 필수입니다.")
            
        if business_number:
            # 숫자만 추출하여 검증
            digits = _digits(business_number)
            if len(digits) != 10:
                raise forms.ValidationError("사업자번호는 10자리 숫자여야 합니다.")
            # 하이픈 추가하여 반환
            return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
            
        return business_number

    def save(self, commit=True):
        """회원 저장 - 비밀번호 해싱"""
        member = super().save(commit=False)
        
        # 비밀번호 설정
        if self.cleaned_data.get("password1"):
            member.password = make_password(self.cleaned_data["password1"])
            
        if commit:
            member.save()
            
        return member


# ─────────────────────────────────────────────────────────────
# 수정 폼 (비밀번호 없는 버전)
# ─────────────────────────────────────────────────────────────
class MemberUpdateForm(forms.ModelForm):
    """
    회원 정보 수정 폼 (비밀번호 제외)
    - 모달에서 사용
    """
    
    class Meta:
        model = Member
        exclude = ['password', 'username']  # 비밀번호, 아이디는 수정 불가
        widgets = _get_form_widgets()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 인스턴스에서 회원 타입 추출
        member_type = None
        if self.instance:
            member_type = getattr(self.instance, 'member_type', '')
            
        # 등급 선택 필드 설정
        self._setup_grade_field(member_type)
        
        # 회원 타입별 필드 구성
        self._configure_fields_by_member_type(member_type)

    def _setup_grade_field(self, member_type):
        """등급 선택 필드 동적 구성 (수정용)"""
        if 'grade' in self.fields:
            try:
                choices = [('', '등급 선택')]
                
                if member_type:
                    grades = MemberGrade.objects.filter(
                        models.Q(member_type=member_type) | models.Q(member_type='ALL'),
                        is_active=True
                    ).order_by('order', 'name')
                    
                    for grade in grades:
                        label = f"[{grade.member_type}] {grade.display_name or grade.name}"
                        choices.append((grade.id, label))
                
                self.fields['grade'].choices = choices
                
            except Exception as e:
                print(f"[forms] 등급 필드 설정 오류: {e}")

    def _configure_fields_by_member_type(self, member_type):
        """회원 타입별 필드 표시/숨김 설정"""
        try:
            b2c_fields = ['gender', 'birth_date', 'nickname', 'recommender_id', 
                         'join_channel', 'is_forever_member']
            b2b_fields = ['company_name', 'business_number', 'representative_name',
                         'business_type', 'business_item', 'company_phone', 'fax', 'company_address']
            
            if member_type == 'B2C':
                for field in b2b_fields:
                    if field in self.fields:
                        self.fields[field].required = False
            elif member_type == 'B2B':
                for field in b2c_fields:
                    if field in self.fields:
                        self.fields[field].required = False
                        
        except Exception as e:
            print(f"[forms] 필드 구성 오류: {e}")

    def clean_phone(self):
        """휴대폰 번호 검증 및 정규화"""
        phone = self.cleaned_data.get("phone", "")
        if phone:
            digits = _digits(phone)
            if digits and len(digits) >= 10:
                if len(digits) == 11:
                    return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
                elif len(digits) == 10:
                    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        return phone