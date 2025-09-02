# members/field_config.py
# ------------------------------------------------------------
# 목적: 회원 관련 모든 필드 정보를 중앙 집중 관리
# 확장성: 프로모션, 주문내역, 등급 등 추후 기능 확장 고려
# 사용처: forms.py, views, templates, API 등에서 공통 참조
# ------------------------------------------------------------

from django.utils import timezone
from datetime import datetime

# ========================================
# 🎯 회원 기본 필드 설정
# ========================================

# 📋 필드 그룹 정의 (탭별 구성)
FIELD_GROUPS = {
    'basic': {
        'name': '기본정보',
        'icon': 'fas fa-user',
        'description': '로그인 정보 및 기본 연락처',
        'required_for': ['B2C', 'B2B'],  # 어떤 회원 타입에 필요한지
    },
    'contact': {
        'name': '연락처정보', 
        'icon': 'fas fa-phone',
        'description': '상세 연락처 및 주소 정보',
        'required_for': ['B2C', 'B2B'],
    },
    'personal': {
        'name': '개인정보',
        'icon': 'fas fa-id-card',
        'description': '개인 특성 및 선호도 (B2C 전용)',
        'required_for': ['B2C'],
    },
    'business': {
        'name': '사업자정보',
        'icon': 'fas fa-briefcase', 
        'description': '사업자 등록 및 회사 정보 (B2B 전용)',
        'required_for': ['B2B'],
    },
    'marketing': {
        'name': '마케팅설정',
        'icon': 'fas fa-bullhorn',
        'description': '프로모션 및 마케팅 수신 설정',
        'required_for': ['B2C', 'B2B'],
    },
    'system': {
        'name': '시스템정보',
        'icon': 'fas fa-cog',
        'description': '계정 상태 및 관리 정보',
        'required_for': ['B2C', 'B2B'],
    },
    # 🆕 향후 확장용 그룹들
    'grade': {
        'name': '등급정보',
        'icon': 'fas fa-crown',
        'description': '회원 등급 및 혜택 정보',
        'required_for': ['B2C', 'B2B'],
        #'coming_soon': True,  # 향후 구현 예정 표시
    },
    'points': {
        'name': '포인트/적립금',
        'icon': 'fas fa-coins',
        'description': '포인트 적립 및 사용 내역',
        'required_for': ['B2C'],
        'coming_soon': True,
    },
    'orders': {
        'name': '주문내역', 
        'icon': 'fas fa-shopping-cart',
        'description': '주문 및 배송 이력',
        'required_for': ['B2C', 'B2B'],
        'coming_soon': True,
    },
    'promotions': {
        'name': '프로모션',
        'icon': 'fas fa-gift',
        'description': '쿠폰, 할인, 이벤트 참여 내역',
        'required_for': ['B2C', 'B2B'], 
        'coming_soon': True,
    },
}

# ========================================
# 📝 필드 상세 정의
# ========================================

MEMBER_FIELDS = {
    # 🔑 기본정보 그룹
    'username': {
        'group': 'basic',
        'label': '아이디',
        'type': 'text',
        'required': True,
        'unique': True,
        'editable': False,  # 수정 불가능한 필드
        'max_length': 30,
        'help_text': '영문, 숫자 조합 4-30자',
        'validation_rules': ['alphanumeric', 'min_length:4'],
        'search_field': True,  # 검색 가능 필드
        'list_display': True,  # 목록에서 표시
        'list_width': '120px',
        'list_align': 'left',
    },
    'password': {
        'group': 'basic',
        'label': '비밀번호',
        'type': 'password',
        'required': True,
        'editable': 'special',  # 특별한 절차로만 수정 가능
        'help_text': '8자 이상, 영문/숫자/특수문자 조합',
        'validation_rules': ['min_length:8', 'password_strength'],
        'exclude_from_api': True,  # API 응답에서 제외
        'exclude_from_form': True,  # 🔧 폼에서도 제외 (별도 필드 사용)
    },
    'name': {
        'group': 'basic',
        'label': '이름',
        'type': 'text',
        'required': True,
        'max_length': 100,
        'search_field': True,
        'list_display': True,
        'list_width': '100px',
        'list_align': 'center',
    },
    'member_type': {
        'group': 'basic',
        'label': '회원유형',
        'type': 'choice',
        'choices': [('B2C', '일반회원'), ('B2B', '사업자회원')],
        'required': True,
        'editable': 'admin_only',  # 관리자만 수정 가능
        'list_display': True,
        'list_width': '90px',
        'list_align': 'center',
        'filter_field': True,  # 필터 옵션으로 사용
    },

    # 📞 연락처정보 그룹  
    'email': {
        'group': 'contact',
        'label': '이메일',
        'type': 'email',
        'required': False,
        'unique': True,
        'search_field': True,
        'list_display': True,
        'list_width': '200px',
        'list_align': 'left',
        'validation_rules': ['email_format', 'domain_check'],
    },
    'phone': {
        'group': 'contact',
        'label': '휴대폰',
        'type': 'tel',
        'required': False,
        'format': 'auto_hyphen',  # 자동 하이픈 삽입
        'search_field': True,
        'list_display': True,
        'list_width': '120px',
        'list_align': 'center',
    },
    'home_phone': {
        'group': 'contact',
        'label': '집전화',
        'type': 'tel',
        'required': False,
        'format': 'auto_hyphen',
    },
    'address': {
        'group': 'contact',
        'label': '주소',
        'type': 'address',
        'required': False,
        'has_detail': True,  # 상세주소 필드 있음
        'readonly': True,  # 주소검색으로만 입력
        'address_search': True,  # 주소검색 버튼 표시
    },
    'zip_code': {
        'group': 'contact',
        'label': '우편번호',
        'type': 'text',
        'required': False,
        'readonly': True,
        'max_length': 10,
    },

    # 👤 개인정보 그룹 (B2C 전용)
    'gender': {
        'group': 'personal',
        'label': '성별',
        'type': 'choice',
        'choices': [('M', '남자'), ('F', '여자')],
        'required': False,
        'member_types': ['B2C'],
        'list_display': True,
        'list_width': '70px',
        'list_align': 'center',
    },
    'birth_date': {
        'group': 'personal',
        'label': '생년월일',
        'type': 'date',
        'required': False,
        'member_types': ['B2C'],
        'list_display': True,
        'list_width': '100px',
        'list_align': 'center',
        'validation_rules': ['past_date', 'adult_check'],
    },
    'nickname': {
        'group': 'personal',
        'label': '닉네임',
        'type': 'text',
        'required': False,
        'member_types': ['B2C'],
        'max_length': 30,
        'unique': True,
    },

    # 🏢 사업자정보 그룹 (B2B 전용)
    'company_name': {
        'group': 'business',
        'label': '회사명',
        'type': 'text',
        'required': 'conditional',  # B2B인 경우에만 필수
        'member_types': ['B2B'],
        'max_length': 255,
        'search_field': True,
    },
    'business_number': {
        'group': 'business', 
        'label': '사업자등록번호',
        'type': 'business_number',
        'required': 'conditional',
        'member_types': ['B2B'],
        'unique': True,
        'format': 'auto_hyphen',  # XXX-XX-XXXXX 형태
        'validation_rules': ['business_number_check'],
    },
    'representative_name': {
        'group': 'business',
        'label': '대표자명',
        'type': 'text',
        'required': False,
        'member_types': ['B2B'],
        'max_length': 100,
    },
    'business_type': {
        'group': 'business',
        'label': '업태',
        'type': 'text',
        'required': False,
        'member_types': ['B2B'],
        'max_length': 100,
    },
    'business_item': {
        'group': 'business',
        'label': '종목',
        'type': 'text',
        'required': False,
        'member_types': ['B2B'],
        'max_length': 100,
    },
    'company_phone': {
        'group': 'business',
        'label': '회사전화',
        'type': 'tel',
        'required': False,
        'member_types': ['B2B'],
        'format': 'auto_hyphen',
    },
    'fax': {
        'group': 'business',
        'label': '팩스',
        'type': 'tel',
        'required': False,
        'member_types': ['B2B'],
        'format': 'auto_hyphen',
    },
    'company_address': {
        'group': 'business',
        'label': '회사주소',
        'type': 'address',
        'required': False,
        'member_types': ['B2B'],
        'has_detail': True,
        'address_search': True,
    },

    # 📢 마케팅설정 그룹
    'marketing_agree': {
        'group': 'marketing',
        'label': '마케팅 수신동의',
        'type': 'boolean',
        'required': False,
        'default': False,
        'help_text': '이벤트, 할인 정보 등 마케팅 정보 수신',
    },
    'is_sms_agree': {
        'group': 'marketing',
        'label': 'SMS 수신동의',
        'type': 'boolean',
        'required': False,
        'default': True,
        'help_text': '주문 관련 SMS 발송',
    },
    'join_channel': {
        'group': 'marketing',
        'label': '가입경로',
        'type': 'choice',
        'choices': [
            ('direct', '직접가입'),
            ('naver', '네이버'),
            ('kakao', '카카오'),
            ('google', '구글'),
            ('facebook', '페이스북'),
            ('recommend', '지인추천'),
            ('ad', '광고'),
        ],
        'required': False,
        'default': 'direct',
        'filter_field': True,
    },
    'recommender_id': {
        'group': 'marketing',
        'label': '추천인 아이디',
        'type': 'text',
        'required': False,
        'member_types': ['B2C'],
        'max_length': 30,
        'help_text': '추천인의 회원 아이디',
    },

    # ⚙️ 시스템정보 그룹
    'is_active': {
        'group': 'system',
        'label': '활성상태',
        'type': 'boolean',
        'required': False,
        'default': True,
        'editable': 'admin_only',
        'list_display': True,
        'list_width': '80px',
        'list_align': 'center',
        'filter_field': True,
    },
    'is_forever_member': {
        'group': 'system',
        'label': '평생회원',
        'type': 'boolean',
        'required': False,
        'default': False,
        'member_types': ['B2C'],
        'help_text': '평생회원 혜택 적용',
    },
    'is_blacklisted': {
        'group': 'system',
        'label': '블랙리스트',
        'type': 'boolean',
        'required': False,
        'default': False,
        'editable': 'admin_only',
        'help_text': '문제 회원 표시',
    },
    'memo': {
        'group': 'system',
        'label': '운영메모',
        'type': 'textarea',
        'required': False,
        'editable': 'admin_only',
        'rows': 3,
        'help_text': '관리자용 메모 (회원에게 노출되지 않음)',
    },
    'created_at': {
        'group': 'system',
        'label': '가입일시',
        'type': 'datetime',
        'required': False,
        'editable': False,
        'exclude_from_form': True,  # 🔧 폼에서 제외
        'list_display': True,
        'list_width': '120px',
        'list_align': 'center',
        'format': 'Y-m-d H:i',
        'filter_field': True,
        'filter_type': 'date_range',
    },
    'point': {
        'group': 'system',
        'label': '보유포인트',
        'type': 'number',
        'required': False,
        'default': 0,
        'editable': 'special',  # 포인트 관리 화면에서만 수정
        'member_types': ['B2C'],
        'format': 'number_comma',  # 천단위 콤마
    },

    # ========================================
    # 👑 등급 관리 그룹 (활성화)
    # ========================================
    'grade': {
        'group': 'grade',
        'label': '회원등급',
        'type': 'choice_foreign',  # 새로운 타입: ForeignKey 선택
        'model': 'MemberGrade',  # 연결할 모델명
        'required': False,
        'editable': True,
        'list_display': True,
        'list_width': '100px',
        'list_align': 'center',
        'filter_field': True,
        'help_text': '회원의 현재 등급',
        # 'coming_soon': False,  # 주석 제거로 활성화
    },
    
    'grade_fixed': {
        'group': 'grade',
        'label': '등급고정',
        'type': 'boolean',
        'required': False,
        'default': False,
        'editable': 'admin_only',  # 관리자만 수정 가능
        'list_display': True,
        'list_width': '80px',
        'list_align': 'center',
        'help_text': '체크 시 자동 승급/강등 방지',
        'icon_true': 'fas fa-lock',
        'icon_false': 'fas fa-unlock',
    },
    
    'grade_fixed_reason': {
        'group': 'grade',
        'label': '고정사유',
        'type': 'textarea',
        'required': False,
        'editable': 'admin_only',
        'rows': 2,
        'help_text': '등급 고정 사유 (관리자용)',
        'depends_on': 'grade_fixed',  # grade_fixed가 True일 때만 표시
    },
    
    'grade_fixed_at': {
        'group': 'grade',
        'label': '고정일시',
        'type': 'datetime',
        'required': False,
        'editable': False,
        'exclude_from_form': True,
        'list_display': False,
        'format': 'Y-m-d H:i',
    },
    
    # ========================================
    # 📊 주문 통계 그룹 (향후 주문 시스템 연동용)
    # ========================================
    'total_orders': {
        'group': 'orders',
        'label': '총 주문수',
        'type': 'number',
        'required': False,
        'default': 0,
        'editable': False,
        'list_display': True,
        'list_width': '80px',
        'list_align': 'center',
        'format': 'number_comma',
        'help_text': '총 주문 횟수 (자동 계산)',
        'coming_soon': True,  # 주문 시스템 완성 후 활성화 예정
    },
    
    'total_spent': {
        'group': 'orders',
        'label': '총 구매금액',
        'type': 'money',
        'required': False,
        'default': 0,
        'editable': False,
        'list_display': True,
        'list_width': '120px',
        'list_align': 'right',
        'format': 'money_comma',
        'help_text': '총 구매 금액 (자동 계산)',
        'coming_soon': True,  # 주문 시스템 완성 후 활성화 예정
    },
    
    'last_order_date': {
        'group': 'orders',
        'label': '최근주문일',
        'type': 'date',
        'required': False,
        'editable': False,
        'exclude_from_form': True,
        'list_display': True,
        'list_width': '100px',
        'list_align': 'center',
        'format': 'Y-m-d',
        'help_text': '마지막 주문 날짜',
        'coming_soon': True,
    },

# FIELD_GROUPS 딕셔너리에서 grade 그룹 활성화
# 기존 'coming_soon': True를 제거하거나 False로 변경:

    'grade': {
        'group': 'grade',
        'label': '회원등급',
        'type': 'choice_foreign',
        'model': 'MemberGrade',
        'required': False,
        'editable': True,
        'list_display': True,
        'list_width': '100px',
        'list_align': 'center',
        'filter_field': True,
        'help_text': '회원의 현재 등급',
        'widget_attrs': {
            'class': 'form-control',
            'id': 'id_grade',
        },
    },
    
    'grade_fixed': {
        'group': 'grade',
        'label': '등급고정',
        'type': 'boolean',
        'required': False,
        'default': False,
        'editable': 'admin_only',
        'list_display': True,
        'list_width': '80px',
        'list_align': 'center',
        'help_text': '체크 시 자동 승급/강등 방지',
        'icon_true': 'fas fa-lock',
        'icon_false': 'fas fa-unlock',
        'widget_attrs': {
            'class': 'form-check-input',
        },
    },
    
    'grade_fixed_reason': {
        'group': 'grade',
        'label': '고정사유',
        'type': 'textarea',
        'required': False,
        'editable': 'admin_only',
        'rows': 2,
        'help_text': '등급 고정 사유 입력',
        'member_types': ['B2C', 'B2B'],
        'placeholder': '예: VIP 계약 고객, 대량구매 고객 등',
        'widget_attrs': {
            'class': 'form-control',
            'rows': 2,
        },
    },
}

# ========================================
# 🛠️ 유틸리티 함수들
# ========================================

def get_fields_by_group(group_name, member_type=None):
    """
    특정 그룹의 필드들을 반환
    
    Args:
        group_name (str): 그룹명 ('basic', 'contact' 등)
        member_type (str): 회원타입 ('B2C', 'B2B') - 필터링용
    
    Returns:
        dict: 해당 그룹의 필드 정의들
    """
    fields = {}
    for field_name, field_config in MEMBER_FIELDS.items():
        # 그룹 매칭
        if field_config.get('group') != group_name:
            continue
            
        # 회원타입 필터링
        if member_type and 'member_types' in field_config:
            if member_type not in field_config['member_types']:
                continue
                
        # 향후 구현 예정 필드 제외
        if field_config.get('coming_soon'):
            continue
            
        fields[field_name] = field_config
        
    return fields

def get_list_display_fields():
    """
    목록 화면에서 표시할 필드들을 반환
    
    Returns:
        list: 목록 표시 필드들의 설정
    """
    display_fields = []
    for field_name, field_config in MEMBER_FIELDS.items():
        if field_config.get('list_display') and not field_config.get('coming_soon'):
            display_fields.append({
                'name': field_name,
                'label': field_config['label'],
                'width': field_config.get('list_width', 'auto'),
                'align': field_config.get('list_align', 'left'),
                'type': field_config['type'],
            })
    
    return sorted(display_fields, key=lambda x: x.get('order', 999))

def get_search_fields():
    """
    검색 가능한 필드들을 반환
    
    Returns:
        list: (field_name, field_label) 튜플 리스트
    """
    search_fields = []
    for field_name, field_config in MEMBER_FIELDS.items():
        if field_config.get('search_field') and not field_config.get('coming_soon'):
            search_fields.append((field_name, field_config['label']))
    
    return search_fields

def get_filter_fields():
    """
    필터링 가능한 필드들을 반환
    
    Returns:
        dict: 필터 필드 설정들
    """
    filter_fields = {}
    for field_name, field_config in MEMBER_FIELDS.items():
        if field_config.get('filter_field') and not field_config.get('coming_soon'):
            filter_fields[field_name] = {
                'label': field_config['label'],
                'type': field_config.get('filter_type', field_config['type']),
                'choices': field_config.get('choices', []),
            }
    
    return filter_fields

def get_required_fields(member_type):
    """
    특정 회원타입에 필요한 필수 필드들을 반환
    
    Args:
        member_type (str): 회원타입 ('B2C' or 'B2B')
    
    Returns:
        list: 필수 필드명 리스트
    """
    required_fields = []
    for field_name, field_config in MEMBER_FIELDS.items():
        # 향후 구현 예정 필드 제외
        if field_config.get('coming_soon'):
            continue
            
        # 회원타입별 필터링
        if 'member_types' in field_config and member_type not in field_config['member_types']:
            continue
            
        # 필수 여부 확인
        is_required = field_config.get('required', False)
        if is_required == True or (is_required == 'conditional' and member_type == 'B2B'):
            required_fields.append(field_name)
    
    return required_fields

def get_editable_fields(user_role='user'):
    """
    수정 가능한 필드들을 반환
    
    Args:
        user_role (str): 사용자 역할 ('user', 'admin')
    
    Returns:
        list: 수정 가능한 필드명 리스트
    """
    editable_fields = []
    for field_name, field_config in MEMBER_FIELDS.items():
        # 향후 구현 예정 필드 제외
        if field_config.get('coming_soon'):
            continue
            
        editable = field_config.get('editable', True)
        
        # 수정 가능 여부 판단
        if editable == True:
            editable_fields.append(field_name)
        elif editable == 'admin_only' and user_role == 'admin':
            editable_fields.append(field_name)
        # 'special', False, 'editable': False인 경우 제외
    
    return editable_fields

# ========================================
# 📋 폼 관련 설정
# ========================================

def get_form_fields(member_type=None, exclude_groups=None):
    """
    폼에서 사용할 필드 설정을 반환
    
    Args:
        member_type (str): 회원타입으로 필드 필터링
        exclude_groups (list): 제외할 그룹 리스트
    
    Returns:
        dict: Django Form에서 사용할 필드 설정
    """
    form_fields = {}
    exclude_groups = exclude_groups or []
    
    for field_name, field_config in MEMBER_FIELDS.items():
        # 향후 구현 예정 필드 제외
        if field_config.get('coming_soon'):
            continue
            
        # 그룹 제외
        if field_config.get('group') in exclude_groups:
            continue
            
        # 회원타입 필터링
        if member_type and 'member_types' in field_config:
            if member_type not in field_config['member_types']:
                continue
                
        # 🔧 폼에서 제외할 필드 (이 부분이 핵심!)
        if field_config.get('exclude_from_form'):
            continue
            
        form_fields[field_name] = field_config
    
    return form_fields

# ========================================
# 🌟 향후 확장 시 이렇게 추가하면 됩니다!
# ========================================

"""
새로운 기능 추가 예시:

1. 쿠폰 기능 추가 시:
   - FIELD_GROUPS에 'coupons' 그룹 추가
   - MEMBER_FIELDS에 쿠폰 관련 필드들 추가
   - coming_soon: False로 변경

2. 등급 시스템 추가 시:
   - 위 주석 처리된 grade 관련 필드들 활성화
   - coming_soon 제거

3. 새로운 필드 타입 추가 시:
   - type에 새로운 타입 정의
   - validation_rules에 새로운 검증 규칙 추가
"""