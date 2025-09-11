# promotion/detail_builder.py
from django.utils import timezone
from decimal import Decimal

class CouponDetailBuilder:
    """쿠폰 상세보기 모달의 섹션과 필드를 동적으로 생성하는 클래스"""
    
    @classmethod
    def build_sections(cls, coupon):
        """쿠폰 객체로부터 상세보기 섹션들을 생성"""
        sections = []
        
        # 기본 정보 섹션
        sections.append(cls._build_basic_info_section(coupon))
        
        # 할인 정보 섹션
        sections.append(cls._build_discount_info_section(coupon))
        
        # 사용 조건 섹션
        sections.append(cls._build_usage_conditions_section(coupon))
        
        # 기간 및 통계 섹션
        sections.append(cls._build_period_stats_section(coupon))
        
        # 생성자 정보 섹션
        sections.append(cls._build_creator_info_section(coupon))
        
        return sections
    
    @classmethod
    def _build_basic_info_section(cls, coupon):
        """기본 정보 섹션"""
        # 현재 상태 계산
        now = timezone.now()
        if not coupon.is_active:
            status_value = "비활성화"
            status_class = "secondary"
        elif now < coupon.start_date:
            status_value = "예정"
            status_class = "warning"
        elif now > coupon.end_date:
            status_value = "만료"
            status_class = "danger"
        else:
            status_value = "활성"
            status_class = "success"
        
        return {
            'title': '기본 정보',
            'icon': 'fas fa-info-circle',
            'header_class': 'bg-primary text-white',
            'layout': 'grid',
            'fields': [
                {
                    'label': '쿠폰명',
                    'value': coupon.name,
                    'col_width': 8,
                    'type': 'text'
                },
                {
                    'label': '쿠폰 코드',
                    'value': coupon.code,
                    'col_width': 4,
                    'type': 'code'
                },
                {
                    'label': '등록번호',
                    'value': f"#{coupon.id}",
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '현재 상태',
                    'value': status_value,
                    'badge_class': status_class,
                    'col_width': 6,
                    'type': 'badge'
                },
                {
                    'label': '설명',
                    'value': coupon.description,
                    'col_width': 12,
                    'type': 'text'
                }
            ]
        }
    
    @classmethod
    def _build_discount_info_section(cls, coupon):
        """할인 정보 섹션"""
        # 할인 타입 표시
        discount_type_display = "정액할인" if coupon.discount_type == 'fixed' else "정률할인"
        
        # 할인 값 표시
        if coupon.discount_type == 'fixed':
            discount_value_display = f"{int(coupon.discount_value):,}원"
        else:
            discount_value_display = f"{coupon.discount_value}%"
        
        # 최대 할인금액 표시
        max_discount_display = "제한 없음"
        if coupon.max_discount_amount:
            max_discount_display = f"{int(coupon.max_discount_amount):,}원"
        
        # 최소 구매금액 표시
        min_purchase_display = "제한 없음"
        if coupon.min_purchase_amount > 0:
            min_purchase_display = f"{int(coupon.min_purchase_amount):,}원 이상"
        
        return {
            'title': '할인 정보',
            'icon': 'fas fa-percent',
            'header_class': 'bg-success text-white',
            'layout': 'grid',
            'fields': [
                {
                    'label': '할인 타입',
                    'value': discount_type_display,
                    'col_width': 4,
                    'type': 'text'
                },
                {
                    'label': '할인 값',
                    'value': discount_value_display,
                    'col_width': 4,
                    'type': 'text'
                },
                {
                    'label': '최대 할인금액',
                    'value': max_discount_display,
                    'col_width': 4,
                    'type': 'text'
                },
                {
                    'label': '최소 구매금액',
                    'value': min_purchase_display,
                    'col_width': 12,
                    'type': 'text'
                }
            ]
        }
    
    @classmethod
    def _build_usage_conditions_section(cls, coupon):
        """사용 조건 섹션"""
        # 사용 제한 표시
        usage_limit_display = "무제한"
        if coupon.usage_limit:
            usage_limit_display = f"{coupon.usage_limit:,}회"
        
        # 대상 회원 표시
        target_member_display = coupon.get_target_member_types_display()
        
        # 대상 등급 표시
        target_grades_display = "모든 등급"
        if coupon.target_grades.exists():
            grades = []
            for grade in coupon.target_grades.all():
                grades.append(f"[{grade.member_type}] {grade.display_name}")
            target_grades_display = ", ".join(grades)
        
        return {
            'title': '사용 조건 및 제한',
            'icon': 'fas fa-cog',
            'header_class': 'bg-warning text-dark',
            'layout': 'grid',
            'fields': [
                {
                    'label': '전체 사용 제한',
                    'value': usage_limit_display,
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '회원별 사용 제한',
                    'value': f"{coupon.usage_limit_per_user}회",
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '대상 회원',
                    'value': target_member_display,
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '대상 등급',
                    'value': target_grades_display,
                    'col_width': 6,
                    'type': 'text'
                }
            ]
        }
    
    @classmethod
    def _build_period_stats_section(cls, coupon):
        """기간 및 통계 섹션"""
        return {
            'title': '기간 및 사용 통계',
            'icon': 'fas fa-calendar-alt',
            'header_class': 'bg-secondary text-white',
            'layout': 'grid',
            'fields': [
                {
                    'label': '시작일시',
                    'value': coupon.start_date.strftime("%Y년 %m월 %d일 %H:%M"),
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '종료일시',
                    'value': coupon.end_date.strftime("%Y년 %m월 %d일 %H:%M"),
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '현재 사용 횟수',
                    'value': f"{coupon.used_count}회",
                    'badge_class': 'info',
                    'col_width': 6,
                    'type': 'badge'
                },
                {
                    'label': '생성일',
                    'value': coupon.created_at.strftime("%Y년 %m월 %d일 %H:%M"),
                    'col_width': 6,
                    'type': 'text'
                }
            ]
        }
    
    @classmethod
    def _build_creator_info_section(cls, coupon):
        """생성자 정보 섹션"""
        # 생성자 표시
        created_by_display = "시스템"
        if coupon.created_by:
            created_by_display = coupon.created_by.username
        
        return {
            'title': '생성자 정보',
            'icon': 'fas fa-user',
            'header_class': 'bg-dark text-white',
            'layout': 'grid',
            'fields': [
                {
                    'label': '생성자',
                    'value': created_by_display,
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '최종 수정일',
                    'value': coupon.updated_at.strftime("%Y년 %m월 %d일 %H:%M"),
                    'col_width': 6,
                    'type': 'text'
                }
            ]
        }