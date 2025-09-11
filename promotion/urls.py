# promotion/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ========================================
    # 대시보드
    # ========================================
    path('', views.promotion_dashboard, name='promotion_dashboard'),
    
    # ========================================
    # 쿠폰 관리
    # ========================================
    path('coupons', views.coupon_list, name='coupon_list'),
    path('coupons/create', views.coupon_create, name='coupon_create'),
    path('coupons/<int:coupon_id>', views.coupon_detail, name='coupon_detail'),
    path('coupons/<int:coupon_id>/edit', views.coupon_edit, name='coupon_edit'),
    path('coupons/<int:coupon_id>/delete', views.delete_coupon, name='coupon_delete'),
    path('coupons/bulk-create', views.coupon_bulk_create, name='coupon_bulk_create'),
    path('coupons/<int:coupon_id>/toggle', views.toggle_coupon_status, name='coupon_toggle_status'),
    path('coupons/export/csv', views.export_coupons_csv, name='coupon_export_csv'),

    # ========================================
    # 이벤트 관리
    # ========================================
    path('events', views.event_list, name='event_list'),
    path('events/create', views.event_create, name='event_create'),
    path('events/<int:event_id>', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/edit', views.event_edit, name='event_edit'),
    path('events/<int:event_id>/delete', views.delete_event, name='event_delete'),
    path('events/<int:event_id>/toggle', views.toggle_event_status, name='event_toggle_status'),
    path('events/<int:pk>/detail-modal/', views.event_detail_modal, name='event_detail_modal'),

    # ========================================
    # 프로모션 규칙
    # ========================================
    path('rules', views.rule_settings, name='promotion_rule_settings'),

    # ========================================
    # AJAX API
    # ========================================
    path('api/validate-coupon', views.validate_coupon_ajax, name='validate_coupon_ajax'),
    path('api/calculate-discount', views.calculate_discount_ajax, name='calculate_discount_ajax'),

    # ✅ 쿠폰 상세보기 모달 (AJAX 템플릿)
    path('coupons/<int:pk>/detail-modal/', views.coupon_detail_modal, name='coupon_detail_modal'),
]
