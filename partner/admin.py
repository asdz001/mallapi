from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.db.models import Sum, Count

# ✅ 안전한 모델 import
try:
    from pricing.models import PartnerUser
    from shop.models import OrderDashboard, Order, OrderItem
    MODELS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 모델 import 오류: {e}")
    MODELS_AVAILABLE = False

from decimal import Decimal

# ✅ 모델이 사용 가능한 경우에만 Admin 등록
if MODELS_AVAILABLE:
    # ✅ 거래처 사용자 관리 Admin
    @admin.register(PartnerUser)
    class PartnerUserAdmin(admin.ModelAdmin):
        list_display = (
            'username', 'email', 'retailer', 'department', 
            'phone', 'is_active', 'created_at_short'
        )
        list_filter = ('retailer', 'is_active', 'created_at')
        search_fields = ('user__username', 'user__email', 'retailer__name', 'department')
        ordering = ('-created_at',)
        fields = ('retailer', 'department', 'phone', 'is_active')
        
        def username(self, obj):
            return obj.user.username
        username.short_description = "사용자명"
        
        def email(self, obj):
            return obj.user.email
        email.short_description = "이메일"
        
        def created_at_short(self, obj):
            return obj.created_at.strftime("%y.%m.%d %I:%M%p")
        created_at_short.short_description = "생성일"
        
        def save_model(self, request, obj, form, change):
            if not change:  # 새로 생성할 때만
                # 자동으로 Django User 생성
                username = f"partner_{obj.retailer.code.lower()}"
                email = f"{obj.retailer.code.lower()}@partner.mallapi.com"
                
                # 이미 존재하는 사용자명이면 숫자 추가
                counter = 1
                original_username = username
                while User.objects.filter(username=username).exists():
                    username = f"{original_username}_{counter}"
                    counter += 1
                
                # 사용자 생성
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password="mallapi2025!",  # 초기 비밀번호
                    first_name=obj.retailer.name,
                    is_staff=True  # Admin 접근 권한
                )
                
                # PartnerUser에 User 연결
                obj.user = user
            
            super().save_model(request, obj, form, change)
        
        def get_readonly_fields(self, request, obj=None):
            if obj:  # 수정할 때
                return self.readonly_fields + ('retailer',)
            return self.readonly_fields


    # ✅ 주문 대시보드 Admin (거래처별 권한 관리)
    @admin.register(OrderDashboard)
    class PartnerOrderDashboardAdmin(admin.ModelAdmin):
        list_display = (
            'order_reference', 'retailer', 'auto_order_number', 
            'partner_status', 'order_detail_display', 'created_at_short'
        )
        list_filter = ('retailer', 'partner_status', 'created_at')
        search_fields = ('order_reference', 'auto_order_number', 'retailer__name')
        ordering = ('-created_at',)
        readonly_fields = ('order_reference', 'auto_order_number', 'order_detail_display')
        fields = ('order', 'retailer', 'partner_status', 'order_summary', 'order_reference', 'auto_order_number')
        
        def order_detail_display(self, obj):
            """주문 상세 정보를 테이블 형태로 표시"""
            try:
                order = obj.order
                items = order.items.select_related('product', 'option').all()
                
                if not items:
                    return format_html("<span style='color: gray;'>주문 상품 없음</span>")
                
                # 주문 요약 계산
                total_qty = sum(item.quantity for item in items)
                total_krw = sum(item.quantity * (item.price_krw or 0) for item in items)
                
                # HTML 테이블 생성
                html = "<div style='max-width: 800px;'>"
                html += f"<p><strong>주문 요약:</strong> {total_qty}개 상품, ₩{total_krw:,}</p>"
                html += "<table style='border-collapse: collapse; width: 100%; font-size: 12px;'>"
                html += """
                <tr style='background-color: #f0f0f0;'>
                    <th style='border: 1px solid #ddd; padding: 5px;'>브랜드</th>
                    <th style='border: 1px solid #ddd; padding: 5px;'>상품명</th>
                    <th style='border: 1px solid #ddd; padding: 5px;'>옵션</th>
                    <th style='border: 1px solid #ddd; padding: 5px;'>수량</th>
                    <th style='border: 1px solid #ddd; padding: 5px;'>단가</th>
                    <th style='border: 1px solid #ddd; padding: 5px;'>소계</th>
                </tr>
                """
                
                for item in items:
                    brand = item.product.brand_name or "-"
                    product_name = item.product.product_name[:30] + "..." if len(item.product.product_name) > 30 else item.product.product_name
                    option_name = item.option.option_name if item.option else "-"
                    quantity = item.quantity
                    unit_price = item.price_krw or 0
                    subtotal = quantity * unit_price
                    
                    html += f"""
                    <tr>
                        <td style='border: 1px solid #ddd; padding: 5px;'>{brand}</td>
                        <td style='border: 1px solid #ddd; padding: 5px;'>{product_name}</td>
                        <td style='border: 1px solid #ddd; padding: 5px;'>{option_name}</td>
                        <td style='border: 1px solid #ddd; padding: 5px; text-align: center;'>{quantity}개</td>
                        <td style='border: 1px solid #ddd; padding: 5px; text-align: right;'>₩{unit_price:,}</td>
                        <td style='border: 1px solid #ddd; padding: 5px; text-align: right;'>₩{subtotal:,}</td>
                    </tr>
                    """
                
                html += "</table></div>"
                return format_html(html)
                
            except Exception as e:
                return format_html(f"<span style='color: red;'>오류: {e}</span>")
        
        order_detail_display.short_description = "주문 상세"
        
        def created_at_short(self, obj):
            return obj.created_at.strftime("%y.%m.%d %I:%M%p")
        created_at_short.short_description = "생성일"
        
        def get_queryset(self, request):
            queryset = super().get_queryset(request)
            
            # PartnerUser인 경우 자신의 거래처 주문만 보기
            if hasattr(request.user, 'partneruser'):
                partner_user = request.user.partneruser
                return queryset.filter(retailer=partner_user.retailer)
            
            # 슈퍼유저는 모든 주문 보기
            return queryset
        
        def has_change_permission(self, request, obj=None):
            # PartnerUser는 자신의 거래처 주문만 수정 가능
            if obj and hasattr(request.user, 'partneruser'):
                partner_user = request.user.partneruser
                return obj.retailer == partner_user.retailer
            return super().has_change_permission(request, obj)
        
        def has_delete_permission(self, request, obj=None):
            # PartnerUser는 삭제 불가
            if hasattr(request.user, 'partneruser'):
                return False
            return super().has_delete_permission(request, obj)

else:
    print("⚠️ PartnerUser 또는 OrderDashboard 모델을 찾을 수 없어 Admin 등록을 건너뜁니다.")

# ✅ Admin 사이트 제목 변경
admin.site.site_header = "MallAPI - PARTNER 관리"
admin.site.site_title = "PARTNER Admin"
admin.site.index_title = "거래처 관리 대시보드"
