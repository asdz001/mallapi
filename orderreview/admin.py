from django.contrib import admin
from .models import OrderReview
from django.utils.html import format_html
from .models import RetailerUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import SimpleListFilter



#거래처별 필터링
class RetailerLimitedFilter(SimpleListFilter):
    title = "거래처"
    parameter_name = "retailer"

    def lookups(self, request, model_admin):
        from .models import RetailerUser
        if request.user.is_superuser:
            # 슈퍼유저는 전체 거래처
            return [(retailer_id, retailer_name) for (retailer_id, retailer_name) in model_admin.model.objects.values_list('retailer__id', 'retailer__name').distinct()]
        else:
            try:
                ru = RetailerUser.objects.get(user=request.user)
                return [(r.id, r.name) for r in ru.retailers.all()]
            except RetailerUser.DoesNotExist:
                return []

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(retailer__id=self.value())
        return queryset
    


#유저생성
@admin.register(RetailerUser)
class RetailerUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_retailers']
    list_filter = ['retailers']
    search_fields = ['user__username']
    filter_horizontal = ['retailers']

    def get_retailers(self, obj):
        return ", ".join([r.name for r in obj.retailers.all()])
    get_retailers.short_description = "연결된 거래처"

    



#주문확인
@admin.register(OrderReview)
class OrderReviewAdmin(admin.ModelAdmin):
    list_display = (
        'order_id', 'retailer_name', 'barcode', 'brand_name', 'product_name', 'option_name',
        'quantity', 'cost_price', 'status', 'status_colored', 'memo_flag', 'order_date','last_updated_by', 'last_updated_at' 
    )
    list_editable = ('status',)  # ✅ 상태 필드를 인라인에서 수정 가능하게 설정
    list_filter = ('retailer', 'status')
    search_fields = ('order_item__product__product_name', 'order_item__option__external_option_id')
    
    list_per_page = 50

    # ✅ 주문 추가/수정 시 아래에 보여줄 필드
    readonly_fields = ['order_item', 'retailer', 'last_updated_by', 'last_updated_at', 'display_info']  # 수정 불가하게 표시만

    # ✅ 필드 순서 재정렬 (폼 화면에서 순서대로 나옴)
    fields = ('order_item', 'retailer', 'status', 'memo', 'display_info','last_updated_by', 'last_updated_at')

    def order_id(self, obj):
        return obj.order_item.external_order_number or "-"
    #order_id.short_description = _("주문번호")



    def retailer_display(self, obj):
        return obj.retailer.name
    #retailer_display.short_description = _("거래처")

    
    # ✅ 읽기 전용 필드 설정
    def get_readonly_fields(self, request, obj=None):
        base = ['last_updated_by', 'last_updated_at', 'display_info']
        if not request.user.is_superuser:
            return base + ['retailer', 'order_item']
        return base
     

    


    def retailer_name(self, obj):
        return obj.retailer.name
    #retailer_name.short_description = _("retailer_거래처")

    def barcode(self, obj):
        return obj.order_item.option.external_option_id if obj.order_item.option else "-"
    #barcode.short_description = _("barcode_바코드")

    def brand_name(self, obj):
        return obj.order_item.product.brand_name
    #brand_name.short_description = _("brand_브랜드")

    def product_name(self, obj):
        return obj.order_item.product.product_name
    #product_name.short_description = _("name_상품명")

    def option_name(self, obj):
        return obj.order_item.option.option_name if obj.order_item.option else "-"
    #option_name.short_description = _("option_옵션")

    def quantity(self, obj):
        return obj.order_item.quantity
    #quantity.short_description = _("quantity_수량")

    def cost_price(self, obj):
        if obj.order_item.option and obj.order_item.option.price:
            return f"{obj.order_item.option.price:,.2f} €"
        return "-"
    cost_price.short_description = _("COST")

    def order_date(self, obj):
        local_time = timezone.localtime(obj.order_item.order.created_at)
        return local_time.strftime("%y.%m.%d %I:%M%p")  # ✅ 한국 시간 기준으로 변환
    #order_date.short_description = _("order_date_주문일")


    # ✅ 하단에 보여줄 자동 표시 정보
    def display_info(self, obj):
        if not obj.order_item:
            return _("주문 항목을 먼저 선택하세요.")

        return format_html(
            "<b>거래처:</b> {}<br>"
            "<b>브랜드:</b> {}<br>"
            "<b>모델명:</b> {}<br>"
            "<b>옵션:</b> {}<br>"
            "<b>수량:</b> {}개<br>"
            "<b>COST:</b> {} €<br>"
            "<b>주문일:</b> {}",
            obj.order_item.order.retailer.name,
            obj.order_item.product.brand_name,
            obj.order_item.product.product_name,
            obj.order_item.option.option_name if obj.order_item.option else "-",
            obj.order_item.quantity,
            f"{obj.order_item.option.price:,.2f}" if obj.order_item.option and obj.order_item.option.price else "-",
            obj.order_item.order.created_at.strftime("%y.%m.%d %I:%M%p")
        )
    #display_info.short_description = _("주문 상세 정보")
    

    # ✅ 주문 상태 변경 시 마지막 수정자와 시간을 기록
    def save_model(self, request, obj, form, change):
        if 'status' in form.changed_data:
            obj.last_updated_by = request.user
            from django.utils import timezone
            obj.last_updated_at = timezone.now()
        super().save_model(request, obj, form, change)


    # ✅ 거래처에 따라 주문 필터링
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        retailers = RetailerUser.objects.filter(user=request.user).values_list('retailers', flat=True)
        return qs.filter(retailer__in=retailers) if retailers else qs.none()  
        
    # ✅ 필터링 거래처만 확인
    def get_list_filter(self, request):
        return [RetailerLimitedFilter, 'status']
        

    def status_colored(self, obj):
        color_map = {
            'PENDING': "#f7f4f1",  # 흰색
            'CONFIRMED': '#5cb85c',  # 녹색
            'SHIPPED': "#6eafeb",    # 하늘
            'CANCELED': "#FF0000", # 빨강
        }
        status = obj.status
        bg_color = color_map.get(status, '#f0f0f0')  # 기본 배경색 (없을 경우)
        return format_html(
            '<div style="background-color: {}; padding: 4px 8px; border-radius: 4px; text-align: center;">{}</div>',
            bg_color,
            status
        )
    status_colored.short_description = "status"    
        


    def memo_flag(self, obj):
        if obj.memo:
            return "⭕"
        return "❌"
    memo_flag.short_description = "MEMO"    