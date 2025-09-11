# promotion/utils.py
from decimal import Decimal
from django.utils import timezone
from django.db.models import Q
from .models import Coupon, Event, PromotionRule, CouponUsage
from members.models import Member, MemberGrade

class DiscountCalculator:
    """
    할인 계산 엔진
    - 등급할인, 쿠폰할인, 이벤트할인을 종합적으로 계산
    - 우선순위 및 중복허용 규칙 적용
    """
    
    def __init__(self, user=None, member=None):
        """
        Args:
            user: Django User 객체 (로그인 사용자)
            member: Member 객체 (회원정보, user가 있으면 자동 조회)
        """
        self.user = user
        self.member = member
        
        # member 정보 자동 조회
        if user and not member:
            try:
                self.member = Member.objects.get(username=user.username)
            except Member.DoesNotExist:
                self.member = None
        
        # 활성화된 프로모션 규칙 조회
        self.promotion_rule = PromotionRule.objects.filter(is_active=True).first()
        if not self.promotion_rule:
            # 기본 규칙이 없으면 생성
            self.promotion_rule = PromotionRule.objects.create(
                name="기본 규칙",
                priority_order='grade_first',
                allow_coupon_stack=False,
                allow_grade_coupon_stack=True
            )
    
    def calculate_product_discount(self, product, quantity=1, coupon_codes=None, event_id=None):
        """
        단일 상품에 대한 할인 계산
        
        Args:
            product: Product 객체
            quantity: 수량
            coupon_codes: 적용할 쿠폰 코드 리스트
            event_id: 적용할 이벤트 ID
            
        Returns:
            dict: {
                'original_price': Decimal,  # 원래 가격
                'final_price': Decimal,     # 최종 가격
                'total_discount': Decimal,  # 총 할인액
                'applied_discounts': [{     # 적용된 할인 내역
                    'type': 'grade|coupon|event',
                    'name': '할인명',
                    'discount_amount': Decimal,
                    'description': '설명'
                }],
                'errors': []  # 오류 메시지
            }
        """
        # 기본 가격 계산 (원화 기준)
        if hasattr(product, 'manual_price_krw') and product.manual_price_krw:
            unit_price = product.manual_price_krw
        elif hasattr(product, 'calculated_price_krw') and product.calculated_price_krw:
            unit_price = product.calculated_price_krw
        else:
            unit_price = Decimal('0')
        
        original_total = unit_price * quantity
        
        result = {
            'original_price': original_total,
            'final_price': original_total,
            'total_discount': Decimal('0'),
            'applied_discounts': [],
            'errors': []
        }
        
        if original_total <= 0:
            result['errors'].append("상품 가격이 설정되지 않았습니다")
            return result
        
        # 할인 적용 순서에 따라 계산
        if self.promotion_rule.priority_order == 'grade_first':
            result = self._apply_grade_first_order(result, product, quantity, coupon_codes, event_id)
        elif self.promotion_rule.priority_order == 'coupon_first':
            result = self._apply_coupon_first_order(result, product, quantity, coupon_codes, event_id)
        else:  # best_discount
            result = self._apply_best_discount(result, product, quantity, coupon_codes, event_id)
        
        return result
    
    def _apply_grade_first_order(self, result, product, quantity, coupon_codes, event_id):
        """등급할인 → 쿠폰 → 이벤트 순서 적용"""
        current_price = result['original_price']
        
        # 1. 등급 할인 적용
        if self.member and self.member.grade:
            grade_discount = self._calculate_grade_discount(current_price, self.member.grade)
            if grade_discount > 0:
                current_price -= grade_discount
                result['applied_discounts'].append({
                    'type': 'grade',
                    'name': f'{self.member.grade.display_name} 등급할인',
                    'discount_amount': grade_discount,
                    'description': f'{self.member.grade.discount_rate}% 등급할인'
                })
        
        # 2. 쿠폰 할인 적용
        if coupon_codes and self.promotion_rule.allow_grade_coupon_stack:
            current_price, coupon_discounts, coupon_errors = self._apply_coupons(
                current_price, coupon_codes, product
            )
            result['applied_discounts'].extend(coupon_discounts)
            result['errors'].extend(coupon_errors)
        
        # 3. 이벤트 할인 적용
        if event_id:
            current_price, event_discount = self._apply_event(current_price, event_id, product)
            if event_discount:
                result['applied_discounts'].append(event_discount)
        
        # 최대 할인율 체크
        current_price = self._apply_max_discount_limit(result['original_price'], current_price)
        
        result['final_price'] = current_price
        result['total_discount'] = result['original_price'] - current_price
        
        return result
    
    def _apply_coupon_first_order(self, result, product, quantity, coupon_codes, event_id):
        """쿠폰 → 등급할인 → 이벤트 순서 적용"""
        current_price = result['original_price']
        
        # 1. 쿠폰 할인 먼저 적용
        if coupon_codes:
            current_price, coupon_discounts, coupon_errors = self._apply_coupons(
                current_price, coupon_codes, product
            )
            result['applied_discounts'].extend(coupon_discounts)
            result['errors'].extend(coupon_errors)
        
        # 2. 등급 할인 적용
        if self.member and self.member.grade and self.promotion_rule.allow_grade_coupon_stack:
            grade_discount = self._calculate_grade_discount(current_price, self.member.grade)
            if grade_discount > 0:
                current_price -= grade_discount
                result['applied_discounts'].append({
                    'type': 'grade',
                    'name': f'{self.member.grade.display_name} 등급할인',
                    'discount_amount': grade_discount,
                    'description': f'{self.member.grade.discount_rate}% 등급할인'
                })
        
        # 3. 이벤트 할인 적용
        if event_id:
            current_price, event_discount = self._apply_event(current_price, event_id, product)
            if event_discount:
                result['applied_discounts'].append(event_discount)
        
        current_price = self._apply_max_discount_limit(result['original_price'], current_price)
        result['final_price'] = current_price
        result['total_discount'] = result['original_price'] - current_price
        
        return result
    
    def _apply_best_discount(self, result, product, quantity, coupon_codes, event_id):
        """가장 유리한 할인 자동선택"""
        original_price = result['original_price']
        
        # 각각의 할인 조합을 시뮬레이션해서 최적 조합 찾기
        combinations = [
            # 등급할인만
            self._simulate_grade_only(original_price),
            # 쿠폰할인만 
            self._simulate_coupon_only(original_price, coupon_codes, product),
            # 이벤트할인만
            self._simulate_event_only(original_price, event_id, product),
            # 등급+쿠폰 (허용된 경우)
            self._simulate_grade_coupon(original_price, coupon_codes, product),
        ]
        
        # 가장 할인이 큰 조합 선택
        best_combination = max(combinations, key=lambda x: x['total_discount'])
        
        result.update(best_combination)
        result['final_price'] = original_price - result['total_discount']
        
        return result
    
    def _calculate_grade_discount(self, price, grade):
        """등급 할인 계산"""
        if not grade or not grade.discount_rate:
            return Decimal('0')
        
        discount_rate = Decimal(str(grade.discount_rate)) / 100
        return price * discount_rate
    
    def _apply_coupons(self, current_price, coupon_codes, product):
        """쿠폰 할인 적용"""
        applied_discounts = []
        errors = []
        total_coupon_discount = Decimal('0')
        
        for code in coupon_codes:
            try:
                coupon = Coupon.objects.get(code=code.upper())
                
                # 쿠폰 유효성 검사
                is_valid, message = coupon.is_valid(self.user)
                if not is_valid:
                    errors.append(f"쿠폰 {code}: {message}")
                    continue
                
                # 회원 타입 체크
                if coupon.target_member_types != 'all' and self.member:
                    if coupon.target_member_types != self.member.member_type:
                        errors.append(f"쿠폰 {code}: 회원 타입이 맞지 않습니다")
                        continue
                
                # 등급 체크
                if coupon.target_grades.exists() and self.member:
                    if not coupon.target_grades.filter(id=self.member.grade.id).exists():
                        errors.append(f"쿠폰 {code}: 등급 조건이 맞지 않습니다")
                        continue
                
                # 최소 구매금액 체크
                if current_price < coupon.min_purchase_amount:
                    errors.append(f"쿠폰 {code}: 최소 구매금액 {coupon.min_purchase_amount:,}원 이상 필요")
                    continue
                
                # 할인 계산
                coupon_discount = coupon.calculate_discount(current_price)
                if coupon_discount > 0:
                    current_price -= coupon_discount
                    total_coupon_discount += coupon_discount
                    
                    applied_discounts.append({
                        'type': 'coupon',
                        'name': coupon.name,
                        'discount_amount': coupon_discount,
                        'description': f'쿠폰 코드: {coupon.code}',
                        'coupon_id': coupon.id
                    })
                    
                    # 쿠폰 중복사용 불허 시 첫 번째만 적용
                    if not self.promotion_rule.allow_coupon_stack:
                        break
                
            except Coupon.DoesNotExist:
                errors.append(f"존재하지 않는 쿠폰 코드: {code}")
        
        return current_price, applied_discounts, errors
    
    def _apply_event(self, current_price, event_id, product):
        """이벤트 할인 적용"""
        try:
            event = Event.objects.get(id=event_id, is_active=True)
            
            if not event.is_valid():
                return current_price, None
            
            # 최소 구매금액 체크
            if current_price < event.min_purchase_amount:
                return current_price, None
            
            # 상품 대상 체크 (향후 구현)
            # if not event.target_all_products:
            #     # 카테고리/브랜드 체크 로직
            
            event_discount = event.calculate_discount(current_price)
            if event_discount > 0:
                return current_price - event_discount, {
                    'type': 'event',
                    'name': event.name,
                    'discount_amount': event_discount,
                    'description': f'이벤트 할인: {event.description[:50]}...'
                }
        
        except Event.DoesNotExist:
            pass
        
        return current_price, None
    
    def _apply_max_discount_limit(self, original_price, discounted_price):
        """최대 할인율 제한 적용"""
        max_discount_rate = self.promotion_rule.max_discount_rate / 100
        max_discount_amount = original_price * max_discount_rate
        
        actual_discount = original_price - discounted_price
        if actual_discount > max_discount_amount:
            return original_price - max_discount_amount
        
        return discounted_price
    
    def _simulate_grade_only(self, price):
        """등급할인만 시뮬레이션"""
        if not self.member or not self.member.grade:
            return {'total_discount': Decimal('0'), 'applied_discounts': []}
        
        discount = self._calculate_grade_discount(price, self.member.grade)
        return {
            'total_discount': discount,
            'applied_discounts': [{
                'type': 'grade',
                'name': f'{self.member.grade.display_name} 등급할인',
                'discount_amount': discount,
                'description': f'{self.member.grade.discount_rate}% 등급할인'
            }] if discount > 0 else []
        }
    
    def _simulate_coupon_only(self, price, coupon_codes, product):
        """쿠폰할인만 시뮬레이션"""
        if not coupon_codes:
            return {'total_discount': Decimal('0'), 'applied_discounts': []}
        
        _, coupon_discounts, _ = self._apply_coupons(price, coupon_codes, product)
        total_discount = sum(d['discount_amount'] for d in coupon_discounts)
        
        return {
            'total_discount': total_discount,
            'applied_discounts': coupon_discounts
        }
    
    def _simulate_event_only(self, price, event_id, product):
        """이벤트할인만 시뮬레이션"""
        if not event_id:
            return {'total_discount': Decimal('0'), 'applied_discounts': []}
        
        _, event_discount = self._apply_event(price, event_id, product)
        if event_discount:
            return {
                'total_discount': event_discount['discount_amount'],
                'applied_discounts': [event_discount]
            }
        
        return {'total_discount': Decimal('0'), 'applied_discounts': []}
    
    def _simulate_grade_coupon(self, price, coupon_codes, product):
        """등급+쿠폰 조합 시뮬레이션"""
        if not self.promotion_rule.allow_grade_coupon_stack:
            return {'total_discount': Decimal('0'), 'applied_discounts': []}
        
        discounts = []
        current_price = price
        
        # 등급할인 먼저
        if self.member and self.member.grade:
            grade_discount = self._calculate_grade_discount(current_price, self.member.grade)
            if grade_discount > 0:
                current_price -= grade_discount
                discounts.append({
                    'type': 'grade',
                    'name': f'{self.member.grade.display_name} 등급할인',
                    'discount_amount': grade_discount,
                    'description': f'{self.member.grade.discount_rate}% 등급할인'
                })
        
        # 쿠폰할인 적용
        if coupon_codes:
            _, coupon_discounts, _ = self._apply_coupons(current_price, coupon_codes, product)
            discounts.extend(coupon_discounts)
        
        total_discount = sum(d['discount_amount'] for d in discounts)
        return {
            'total_discount': total_discount,
            'applied_discounts': discounts
        }


# 편의 함수들
def calculate_single_product_discount(product, user=None, quantity=1, coupon_codes=None):
    """
    단일 상품 할인 계산 편의 함수
    
    Args:
        product: Product 객체
        user: User 객체 (선택사항)
        quantity: 수량
        coupon_codes: 쿠폰 코드 리스트
        
    Returns:
        할인 계산 결과 dict
    """
    calculator = DiscountCalculator(user=user)
    return calculator.calculate_product_discount(product, quantity, coupon_codes)


def validate_coupon_code(code, user=None):
    """
    쿠폰 코드 유효성 검사 편의 함수
    
    Args:
        code: 쿠폰 코드
        user: User 객체
        
    Returns:
        (is_valid: bool, message: str, coupon: Coupon|None)
    """
    try:
        coupon = Coupon.objects.get(code=code.upper())
        is_valid, message = coupon.is_valid(user)
        return is_valid, message, coupon
    except Coupon.DoesNotExist:
        return False, "존재하지 않는 쿠폰 코드입니다", None


def get_available_events():
    """
    현재 진행중인 이벤트 목록 반환
    
    Returns:
        QuerySet: 활성화된 Event 목록
    """
    now = timezone.now()
    return Event.objects.filter(
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('priority')


def record_coupon_usage(coupon, user, original_amount, discount_amount, order_id=None):
    """
    쿠폰 사용 내역 기록
    
    Args:
        coupon: Coupon 객체
        user: User 객체
        original_amount: 원래 금액
        discount_amount: 할인 금액
        order_id: 주문번호 (선택사항)
        
    Returns:
        CouponUsage 객체
    """
    usage = CouponUsage.objects.create(
        coupon=coupon,
        user=user,
        order_id=order_id,
        original_amount=original_amount,
        discount_amount=discount_amount,
        final_amount=original_amount - discount_amount
    )
    
    return usage