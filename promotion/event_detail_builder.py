# promotion/event_detail_builder.py
from django.utils import timezone
from decimal import Decimal

class EventDetailBuilder:
    """이벤트 상세보기 모달의 섹션과 필드를 동적으로 생성하는 클래스"""
    
    @classmethod
    def build_sections(cls, event):
        """이벤트 객체로부터 상세보기 섹션들을 생성"""
        sections = []
        
        # 기본 정보 섹션
        sections.append(cls._build_basic_info_section(event))
        
        # 할인 정보 섹션
        sections.append(cls._build_discount_info_section(event))
        
        # 적용 대상 섹션
        sections.append(cls._build_target_section(event))
        
        # 기간 및 조건 섹션
        sections.append(cls._build_period_conditions_section(event))
        
        # 생성 정보 섹션
        sections.append(cls._build_creation_info_section(event))
        
        return sections
    
    @classmethod
    def _build_basic_info_section(cls, event):
        """기본 정보 섹션"""
        # 현재 상태 계산
        now = timezone.now()
        if not event.is_active:
            status_value = "비활성화"
            status_class = "secondary"
        elif now < event.start_date:
            status_value = "예정"
            status_class = "warning"
        elif now > event.end_date:
            status_value = "만료"
            status_class = "danger"
        else:
            status_value = "진행중"
            status_class = "success"
        
        return {
            'title': '기본 정보',
            'icon': 'fas fa-bullhorn',
            'header_class': 'bg-primary text-white',
            'layout': 'grid',
            'fields': [
                {
                    'label': '이벤트명',
                    'value': event.name,
                    'col_width': 8,
                    'type': 'text'
                },
                {
                    'label': '등록번호',
                    'value': f"#{event.id}",
                    'col_width': 4,
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
                    'label': '우선순위',
                    'value': f"{event.priority}",
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '설명',
                    'value': event.description,
                    'col_width': 12,
                    'type': 'text'
                }
            ]
        }
    
    @classmethod
    def _build_discount_info_section(cls, event):
        """할인 정보 섹션"""
        # 할인 타입 표시
        discount_type_display = "정액할인" if event.discount_type == 'fixed' else "정률할인"
        
        # 할인 값 표시
        if event.discount_type == 'fixed':
            discount_value_display = f"{int(event.discount_value):,}원"
        else:
            discount_value_display = f"{event.discount_value}%"
        
        # 최대 할인금액 표시
        max_discount_display = "제한 없음"
        if event.max_discount_amount:
            max_discount_display = f"{int(event.max_discount_amount):,}원"
        
        # 최소 구매금액 표시
        min_purchase_display = "제한 없음"
        if event.min_purchase_amount > 0:
            min_purchase_display = f"{int(event.min_purchase_amount):,}원 이상"
        
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
    def _build_target_section(cls, event):
        """적용 대상 섹션"""
        # 적용 범위 표시
        if event.target_all_products:
            target_scope = "전체 상품"
        else:
            target_scope = "선택 상품"
        
        # 대상 카테고리 표시
        target_categories_display = "지정 없음"
        if event.target_categories:
            if isinstance(event.target_categories, list) and event.target_categories:
                target_categories_display = ", ".join(event.target_categories[:5])  # 최대 5개만 표시
                if len(event.target_categories) > 5:
                    target_categories_display += f" 외 {len(event.target_categories) - 5}개"
        
        # 대상 브랜드 표시
        target_brands_display = "지정 없음"
        if event.target_brands:
            if isinstance(event.target_brands, list) and event.target_brands:
                target_brands_display = ", ".join(event.target_brands[:5])  # 최대 5개만 표시
                if len(event.target_brands) > 5:
                    target_brands_display += f" 외 {len(event.target_brands) - 5}개"
        
        return {
            'title': '적용 대상',
            'icon': 'fas fa-target',
            'header_class': 'bg-info text-white',
            'layout': 'grid',
            'fields': [
                {
                    'label': '적용 범위',
                    'value': target_scope,
                    'col_width': 12,
                    'type': 'text'
                },
                {
                    'label': '대상 카테고리',
                    'value': target_categories_display,
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '대상 브랜드',
                    'value': target_brands_display,
                    'col_width': 6,
                    'type': 'text'
                }
            ]
        }
    
    @classmethod
    def _build_period_conditions_section(cls, event):
        """기간 및 조건 섹션"""
        return {
            'title': '기간 및 조건',
            'icon': 'fas fa-calendar-alt',
            'header_class': 'bg-warning text-dark',
            'layout': 'grid',
            'fields': [
                {
                    'label': '시작일시',
                    'value': event.start_date.strftime("%Y년 %m월 %d일 %H:%M"),
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '종료일시',
                    'value': event.end_date.strftime("%Y년 %m월 %d일 %H:%M"),
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '최소 구매금액',
                    'value': f"{int(event.min_purchase_amount):,}원",
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '우선순위',
                    'value': f"{event.priority} (낮을수록 우선)",
                    'col_width': 6,
                    'type': 'text'
                }
            ]
        }
    
    @classmethod
    def _build_creation_info_section(cls, event):
        """생성 정보 섹션"""
        return {
            'title': '생성 정보',
            'icon': 'fas fa-clock',
            'header_class': 'bg-secondary text-white',
            'layout': 'grid',
            'fields': [
                {
                    'label': '생성일',
                    'value': event.created_at.strftime("%Y년 %m월 %d일 %H:%M"),
                    'col_width': 6,
                    'type': 'text'
                },
                {
                    'label': '최종 수정일',
                    'value': event.updated_at.strftime("%Y년 %m월 %d일 %H:%M"),
                    'col_width': 6,
                    'type': 'text'
                }
            ]
        }