# promotion/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .detail_builder import CouponDetailBuilder
from .event_detail_builder import EventDetailBuilder
import json
import csv

from .models import Coupon, Event, PromotionRule, CouponUsage
from .forms import (
    CouponForm, EventForm, PromotionRuleForm, 
    CouponBulkCreateForm, CouponSearchForm
)
from .utils import DiscountCalculator, validate_coupon_code, get_available_events


# ========================================
# 대시보드 뷰
# ========================================

@login_required
def promotion_dashboard(request):
    """
    프로모션 대시보드 - 전체 현황 및 통계
    """
    now = timezone.now()
    
    # 기본 통계
    stats = {
        'total_coupons': Coupon.objects.count(),
        'active_coupons': Coupon.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).count(),
        'total_events': Event.objects.count(),
        'active_events': Event.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).count(),
        'usage_today': CouponUsage.objects.filter(
            used_at__date=now.date(),
            status='used'
        ).count(),
        'usage_this_month': CouponUsage.objects.filter(
            used_at__year=now.year,
            used_at__month=now.month,
            status='used'
        ).count(),
    }
    
    # 최근 생성된 쿠폰
    recent_coupons = Coupon.objects.order_by('-created_at')[:5]
    
    # 최근 사용된 쿠폰
    recent_usages = CouponUsage.objects.filter(
        status='used'
    ).select_related('coupon', 'user').order_by('-used_at')[:10]
    
    # 진행중인 이벤트
    active_events = Event.objects.filter(
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by('end_date')[:5]
    
    # 인기 쿠폰 (사용횟수 기준)
    popular_coupons = Coupon.objects.filter(
        used_count__gt=0
    ).order_by('-used_count')[:5]
    
    context = {
        'stats': stats,
        'recent_coupons': recent_coupons,
        'recent_usages': recent_usages,
        'active_events': active_events,
        'popular_coupons': popular_coupons,
    }
    
    return render(request, 'dashboard/promotion/dashboard.html', context)


# ========================================
# 쿠폰 관리 뷰
# ========================================

@login_required
def coupon_list(request):
    """
    쿠폰 목록 조회 - 검색, 필터링, 페이징 지원
    """
    search_form = CouponSearchForm(request.GET)
    coupons = Coupon.objects.all().order_by('-created_at')
    
    # 검색 처리
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        discount_type = search_form.cleaned_data.get('discount_type')
        status = search_form.cleaned_data.get('status')
        target_member_type = search_form.cleaned_data.get('target_member_type')
        
        if search_query:
            coupons = coupons.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query)
            )
        
        if discount_type:
            coupons = coupons.filter(discount_type=discount_type)
        
        if target_member_type:
            coupons = coupons.filter(target_member_types=target_member_type)
        
        # 상태별 필터링
        if status == 'active':
            now = timezone.now()
            coupons = coupons.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now
            )
        elif status == 'inactive':
            coupons = coupons.filter(is_active=False)
        elif status == 'expired':
            now = timezone.now()
            coupons = coupons.filter(end_date__lt=now)
    
    # 페이징 처리
    paginator = Paginator(coupons, 25)  # 25개씩 표시
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 통계 정보
    stats = {
        'total_coupons': Coupon.objects.count(),
        'active_coupons': Coupon.objects.filter(
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).count(),
        'used_today': CouponUsage.objects.filter(
            used_at__date=timezone.now().date(),
            status='used'
        ).count(),
    }
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'stats': stats,
        #'now': timezone.now(),
    }
    
    return render(request, 'dashboard/promotion/coupon_list.html', context)


@login_required
def coupon_create(request):
    """
    쿠폰 생성
    """
    if request.method == 'POST':
        if request.method == 'POST':
            print("=== POST 데이터 ===")
            print(request.POST)
        
            form = CouponForm(request.POST)
            print("=== 폼 유효성 검사 ===")
            print(f"form.is_valid(): {form.is_valid()}")
        
            if not form.is_valid():
                print("=== 폼 오류 ===")
                print(form.errors)
                print("=== 필드별 오류 ===")
                for field, errors in form.errors.items():
                    print(f"{field}: {errors}")
                    
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save(commit=False)
            coupon.created_by = request.user
            coupon.save()
            form.save_m2m()  # ManyToMany 필드 저장
            
            messages.success(request, f'쿠폰 "{coupon.name}" ({coupon.code})이 생성되었습니다.')
            return redirect('dashboard:coupon_list')
        else:
            messages.error(request, '쿠폰 생성 중 오류가 발생했습니다. 입력 내용을 확인해주세요.')
    else:
        form = CouponForm()
    
    context = {
        'form': form,
        'is_edit': False,
    }
    
    return render(request, 'dashboard/promotion/coupon_form.html', context)


@login_required
def coupon_edit(request, coupon_id):
    """
    쿠폰 수정
    """
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, f'쿠폰 "{coupon.name}"이 수정되었습니다.')
            return redirect('dashboard:coupon_list')
        else:
            messages.error(request, '쿠폰 수정 중 오류가 발생했습니다.')
    else:
        form = CouponForm(instance=coupon)
    
    context = {
        'form': form,
        'coupon': coupon,
        'is_edit': True,
    }
    
    return render(request, 'dashboard/promotion/coupon_form.html', context)


@login_required
def coupon_detail(request, coupon_id):
    """
    쿠폰 상세 정보 및 사용 내역
    """
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    # 사용 내역 조회
    usages = CouponUsage.objects.filter(coupon=coupon).order_by('-used_at')
    usage_paginator = Paginator(usages, 20)
    usage_page = usage_paginator.get_page(request.GET.get('usage_page'))
    
    # 통계 정보
    usage_stats = {
        'total_used': usages.filter(status='used').count(),
        'total_cancelled': usages.filter(status='cancelled').count(),
        'usage_rate': 0,
    }
    
    if coupon.usage_limit:
        usage_stats['usage_rate'] = (usage_stats['total_used'] / coupon.usage_limit) * 100
    
    context = {
        'coupon': coupon,
        'usage_page': usage_page,
        'usage_stats': usage_stats,
    }
    
    return render(request, 'dashboard/promotion/coupon_detail.html', context)


@login_required
def coupon_bulk_create(request):
    """
    쿠폰 대량 생성
    """
    if request.method == 'POST':
        form = CouponBulkCreateForm(request.POST)
        if form.is_valid():
            # 대량 생성 로직
            created_coupons = []
            base_name = form.cleaned_data['base_name']
            quantity = form.cleaned_data['quantity']
            code_prefix = form.cleaned_data['code_prefix']
            
            try:
                for i in range(quantity):
                    # 쿠폰 코드 생성
                    if code_prefix:
                        code = f"{code_prefix}{Coupon.generate_code(6)}"
                    else:
                        code = Coupon.generate_code()
                    
                    coupon = Coupon.objects.create(
                        name=f"{base_name} #{i+1:03d}",
                        code=code,
                        discount_type=form.cleaned_data['discount_type'],
                        discount_value=form.cleaned_data['discount_value'],
                        start_date=form.cleaned_data['start_date'],
                        end_date=form.cleaned_data['end_date'],
                        created_by=request.user
                    )
                    created_coupons.append(coupon)
                
                messages.success(
                    request,
                    f'{quantity}개의 쿠폰이 성공적으로 생성되었습니다.'
                )
                return redirect('dashboard:coupon_list')
                
            except Exception as e:
                # 생성 중 오류 발생 시 이미 생성된 쿠폰들 정리
                for coupon in created_coupons:
                    coupon.delete()
                
                messages.error(request, f'쿠폰 대량 생성 중 오류가 발생했습니다: {str(e)}')
        else:
            messages.error(request, '입력 내용을 확인해주세요.')
    else:
        form = CouponBulkCreateForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'dashboard/promotion/coupon_bulk_create.html', context)


# ========================================
# 이벤트 관리 뷰
# ========================================

@login_required
def event_list(request):
    """
    이벤트 할인 목록
    """
    events = Event.objects.all().order_by('-created_at')
    
    # 검색 처리
    search = request.GET.get('search')
    if search:
        events = events.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # 상태별 필터링
    status = request.GET.get('status')
    if status == 'active':
        now = timezone.now()
        events = events.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )
    elif status == 'inactive':
        events = events.filter(is_active=False)
    elif status == 'expired':
        now = timezone.now()
        events = events.filter(end_date__lt=now)
    
    # 페이징
    paginator = Paginator(events, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status': status,
    }
    
    return render(request, 'dashboard/promotion/event_list.html', context)


@login_required
def event_create(request):
    """
    이벤트 생성
    """
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save()
            messages.success(request, f'이벤트 "{event.name}"이 생성되었습니다.')
            return redirect('dashboard:event_list')
        else:
            messages.error(request, '이벤트 생성 중 오류가 발생했습니다.')
    else:
        form = EventForm()
    
    context = {
        'form': form,
        'is_edit': False,
    }
    
    return render(request, 'dashboard/promotion/event_form.html', context)


@login_required
def event_edit(request, event_id):
    """
    이벤트 수정
    """
    event = get_object_or_404(Event, id=event_id)
    
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f'이벤트 "{event.name}"이 수정되었습니다.')
            return redirect('dashboard:event_list')
        else:
            messages.error(request, '이벤트 수정 중 오류가 발생했습니다.')
    else:
        form = EventForm(instance=event)
    
    context = {
        'form': form,
        'event': event,
        'is_edit': True,
    }
    
    return render(request, 'dashboard/promotion/event_form.html', context)


@login_required
def event_detail(request, event_id):
    """
    이벤트 상세 정보
    """
    event = get_object_or_404(Event, id=event_id)
    
    context = {
        'event': event,
    }
    
    return render(request, 'dashboard/promotion/event_detail.html', context)


# ========================================
# 프로모션 규칙 관리 뷰
# ========================================

@login_required
def rule_settings(request):
    """
    프로모션 규칙 설정 - 할인 우선순위 및 중복 허용 규칙 관리
    """
    # 기본 규칙 조회 또는 생성
    rule = PromotionRule.objects.filter(is_active=True).first()
    
    if request.method == 'POST':
        if rule:
            form = PromotionRuleForm(request.POST, instance=rule)
        else:
            form = PromotionRuleForm(request.POST)
        
        if form.is_valid():
            # 기존 활성 규칙들 비활성화
            PromotionRule.objects.filter(is_active=True).update(is_active=False)
            
            # 새 규칙 저장
            new_rule = form.save()
            messages.success(request, '프로모션 규칙이 저장되었습니다.')
            return redirect('dashboard:promotion_rule_settings')
        else:
            messages.error(request, '규칙 저장 중 오류가 발생했습니다.')
    else:
        if rule:
            form = PromotionRuleForm(instance=rule)
        else:
            form = PromotionRuleForm()
    
    context = {
        'form': form,
        'rule': rule,
    }
    
    return render(request, 'dashboard/promotion/rule_settings.html', context)


# ========================================
# AJAX API 뷰
# ========================================

@login_required
@require_http_methods(["POST"])
def toggle_coupon_status(request, coupon_id):
    """
    쿠폰 활성화/비활성화 토글
    """
    try:
        coupon = get_object_or_404(Coupon, id=coupon_id)
        coupon.is_active = not coupon.is_active
        coupon.save()
        
        return JsonResponse({
            'success': True,
            'is_active': coupon.is_active,
            'message': f'쿠폰이 {"활성화" if coupon.is_active else "비활성화"}되었습니다.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
@require_http_methods(["POST"])
def toggle_event_status(request, event_id):
    """
    이벤트 활성화/비활성화 토글
    """
    try:
        event = get_object_or_404(Event, id=event_id)
        event.is_active = not event.is_active
        event.save()
        
        return JsonResponse({
            'success': True,
            'is_active': event.is_active,
            'message': f'이벤트가 {"활성화" if event.is_active else "비활성화"}되었습니다.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def validate_coupon_ajax(request):
    """
    쿠폰 코드 유효성 검사 AJAX - 실시간 쿠폰 검증
    """
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip()
        
        if not code:
            return JsonResponse({
                'valid': False,
                'message': '쿠폰 코드를 입력해주세요.'
            })
        
        is_valid, message, coupon = validate_coupon_code(code, request.user)
        
        response_data = {
            'valid': is_valid,
            'message': message
        }
        
        if is_valid and coupon:
            response_data.update({
                'coupon': {
                    'name': coupon.name,
                    'discount_type': coupon.get_discount_type_display(),
                    'discount_value': str(coupon.discount_value),
                    'min_purchase_amount': str(coupon.min_purchase_amount),
                }
            })
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'message': f'검증 중 오류가 발생했습니다: {str(e)}'
        })


@login_required
def calculate_discount_ajax(request):
    """
    할인 계산 AJAX - 상품별 할인 금액 실시간 계산
    """
    try:
        product_id = request.GET.get('product_id')
        quantity = int(request.GET.get('quantity', 1))
        coupon_codes = request.GET.getlist('coupon_codes[]')
        event_id = request.GET.get('event_id')
        
        if not product_id:
            return JsonResponse({
                'success': False,
                'message': '상품 ID가 필요합니다.'
            })
        
        # 상품 조회 (shop.Product 모델 사용)
        from shop.models import Product
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '존재하지 않는 상품입니다.'
            })
        
        # 할인 계산
        calculator = DiscountCalculator(user=request.user)
        result = calculator.calculate_product_discount(
            product=product,
            quantity=quantity,
            coupon_codes=coupon_codes,
            event_id=event_id
        )
        
        return JsonResponse({
            'success': True,
            'original_price': str(result['original_price']),
            'final_price': str(result['final_price']),
            'total_discount': str(result['total_discount']),
            'discount_rate': round((result['total_discount'] / result['original_price']) * 100, 2) if result['original_price'] > 0 else 0,
            'applied_discounts': result['applied_discounts'],
            'errors': result['errors']
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'계산 중 오류가 발생했습니다: {str(e)}'
        })


# ========================================
# 유틸리티 뷰
# ========================================

@login_required
def export_coupons_csv(request):
    """
    쿠폰 목록 CSV 내보내기
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="coupons.csv"'
    response.write('\ufeff')  # BOM for Excel UTF-8 support
    
    writer = csv.writer(response)
    writer.writerow([
        '쿠폰명', '코드', '할인타입', '할인값', '최소구매금액',
        '사용제한', '개인제한', '시작일', '종료일', '대상회원',
        '활성화', '사용횟수', '생성일'
    ])
    
    coupons = Coupon.objects.all().order_by('-created_at')
    
    for coupon in coupons:
        writer.writerow([
            coupon.name,
            coupon.code,
            coupon.get_discount_type_display(),
            coupon.discount_value,
            coupon.min_purchase_amount,
            coupon.usage_limit or '무제한',
            coupon.usage_limit_per_user,
            coupon.start_date.strftime('%Y-%m-%d %H:%M'),
            coupon.end_date.strftime('%Y-%m-%d %H:%M'),
            coupon.get_target_member_types_display(),
            '활성화' if coupon.is_active else '비활성화',
            coupon.used_count,
            coupon.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    
    return response


# ========================================
# 삭제 뷰
# ========================================

@login_required
@require_http_methods(["POST"])
def delete_coupon(request, coupon_id):
    """
    쿠폰 삭제
    - JS에서 fetch(POST)로 호출 시: JSON 응답
    - 일반 폼/링크로 호출 시: 메시지 + 리다이렉트
    """
    try:
        coupon = get_object_or_404(Coupon, id=coupon_id)

        # 사용된 쿠폰은 삭제 금지
        if coupon.used_count > 0:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': '이미 사용된 쿠폰은 삭제할 수 없습니다.'})
            messages.error(request, '이미 사용된 쿠폰은 삭제할 수 없습니다.')
            return redirect('dashboard:coupon_detail', coupon_id=coupon_id)

        coupon_name = coupon.name
        coupon.delete()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'쿠폰 "{coupon_name}"이 삭제되었습니다.'})

        messages.success(request, f'쿠폰 "{coupon_name}"이 삭제되었습니다.')
        return redirect('dashboard:coupon_list')

    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': f'삭제 중 오류: {str(e)}'})
        messages.error(request, f'삭제 중 오류가 발생했습니다: {str(e)}')
        return redirect('dashboard:coupon_list')


@login_required
@require_http_methods(["POST"])
def delete_event(request, event_id):
    """
    이벤트 삭제
    """
    try:
        event = get_object_or_404(Event, id=event_id)
        event_name = event.name
        event.delete()
        
        messages.success(request, f'이벤트 "{event_name}"이 삭제되었습니다.')
        return redirect('dashboard:event_list')
        
    except Exception as e:
        messages.error(request, f'삭제 중 오류가 발생했습니다: {str(e)}')
        return redirect('dashboard:event_list')
    


@login_required
def coupon_detail_modal(request, pk):
    """
    쿠폰 상세보기 모달 (템플릿 렌더링 방식)
    - 모달 HTML을 동적으로 생성하여 반환
    """
    try:
        coupon = get_object_or_404(Coupon, id=pk)
        
        # CouponDetailBuilder를 사용하여 섹션 구성
        sections = CouponDetailBuilder.build_sections(coupon)
        
        # 모달 템플릿 렌더링
        return render(request, 'dashboard/promotion/coupon_detail_modal.html', {
            'coupon': coupon,
            'sections': sections,
        })
        
    except Exception as e:
        # 오류 발생 시 간단한 모달 반환
        return render(request, 'dashboard/promotion/coupon_detail_error.html', {
            'error_message': f'쿠폰 정보를 불러오는데 실패했습니다: {str(e)}'
        })

# 파일 마지막에 추가할 뷰 함수
@login_required
def event_detail_modal(request, pk):
    """
    이벤트 상세보기 모달 (템플릿 렌더링 방식)
    - 모달 HTML을 동적으로 생성하여 반환
    """
    try:
        event = get_object_or_404(Event, id=pk)
        
        # EventDetailBuilder를 사용하여 섹션 구성
        sections = EventDetailBuilder.build_sections(event)
        
        # 모달 템플릿 렌더링
        return render(request, 'dashboard/promotion/event_detail_modal.html', {
            'event': event,
            'sections': sections,
        })
        
    except Exception as e:
        # 오류 발생 시 간단한 모달 반환 (쿠폰과 동일한 패턴)
        return render(request, 'dashboard/promotion/event_detail_error.html', {
            'error_message': f'이벤트 정보를 불러오는데 실패했습니다: {str(e)}'
        })