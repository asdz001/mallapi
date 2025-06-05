from django.contrib import admin
from .models import Product, Order, ProductOption, OrderItem, RawProduct, RawProductOption
from .models import Cart  # ✅ OrderDashboard Admin은 partner 앱으로 이동했으므로 제거
from django.contrib import messages
from pricing.models import CountryAlias  # ✅ PartnerUser import 제거
from shop.services.order_service import create_orders_from_carts
from django.utils.html import format_html, format_html_join
from shop.utils.markup_util import get_markup_from_product
from shop.services.product.conversion_service import convert_or_update_product
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Count
from django.contrib.staticfiles.storage import staticfiles_storage
from django.conf import settings


# ✅ 브랜드 필터 - 모든 브랜드 + 수량 표시
class BrandCountListFilter(admin.SimpleListFilter):
    title = '브랜드'
    parameter_name = 'brand_name'
    
    def lookups(self, request, model_admin):
        # 모든 브랜드를 상품 수와 함께 표시
        brands = Product.objects.values('brand_name').annotate(
            count=Count('id')
        ).order_by('brand_name')
        
        result = []
        for brand in brands:
            if brand['brand_name']:
                result.append((
                    brand['brand_name'], 
                    f"{brand['brand_name']} ({brand['count']}개)"
                ))
        return result
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(brand_name=self.value())
        return queryset


# ✅ 성능 최적화된 원본상품 재고 인라인
class RawProductOptionInline(admin.TabularInline):
    model = RawProductOption
    extra = 1
    fields = ('external_option_id', 'option_name', 'stock', 'price')


# ✅ 원본상품 가공상품으로 전송버튼 (액션 최적화)
@admin.action(description="선택한 상품을 가공상품으로 등록/수정")
def convert_selected_raw_products(modeladmin, request, queryset):
    success_count = 0
    fail_count = 0
    
    # ✅ prefetch_related로 옵션 데이터를 한 번에 가져옴
    queryset = queryset.prefetch_related('options')
    
    for raw_product in queryset:
        try:
            if convert_or_update_product(raw_product):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            fail_count += 1
            messages.error(request, f"상품 {raw_product.product_name} 변환 중 오류: {str(e)}")
    
    messages.success(request, f"{success_count}건 등록 성공, {fail_count}건 실패 (로그 확인 필요)")


# ✅ 성능 최적화된 원본상품 관리자
@admin.register(RawProduct)
class RawProductAdmin(admin.ModelAdmin):
    list_display = ('retailer', 'external_product_id','combined_category', 'image_preview','season', 'raw_brand_name', 'product_name', 'sku',
                      'price_retail','discount_rate', 'price_org' ,'origin' ,  'option_summary' ,  'status', 'created_at_short','updated_at_short' )

    inlines = [RawProductOptionInline]
    list_filter = ('retailer' , 'status', 'created_at')
    search_fields = ('product_name', 'raw_brand_name', 'sku' ,'external_product_id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    actions = [convert_selected_raw_products]
    change_list_template = 'admin/shop/rawproduct/change_list_with_count.html'
    
    # ✅ 페이지네이션 설정 (30초 → 2초 핵심)
    list_per_page = 50  # 페이지당 50개 항목
    list_max_show_all = 200  # "모두 보기" 최대 200개
    
    # ✅ 쿼리 최적화 - prefetch_related로 options를 미리 로드
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related('options')

    # 카테고리
    def combined_category(self, obj):
        parts = [obj.gender, obj.category1, obj.category2]
        return " > ".join([p for p in parts if p])
    combined_category.short_description = "카테고리"

    # 이미지
    def image_preview(self, obj):
        urls = [obj.image_url_1, obj.image_url_2, obj.image_url_3, obj.image_url_4]
        tags = [
            format_html(
                '''
                <img src="{}" style="width:60px; height:60px; margin-right:4px; transition:0.3s;" 
                     onmouseover="this.style.transform='scale(3)'" 
                     onmouseout="this.style.transform='scale(1)'"/>
                ''', url
            ) for url in urls if url
        ]
        return format_html(''.join(tags)) if tags else "-"
    image_preview.short_description = "이미지"
    
    # ✅ 재고옵션 (이미 prefetch된 데이터 사용)
    def option_summary(self, obj):
        options = getattr(obj, '_prefetched_objects_cache', {}).get('options')
        if options is None:
            options = list(obj.options.all())
        
        if not options:
            return "-"
        return format_html("<br>".join(
            f"{opt.option_name} : {opt.stock}" for opt in options
        ))
    option_summary.short_description = "재고옵션"

    # ✅ 1번 요청: 날짜 형식 변경 (25.06.05 8:22AM)
    def created_at_short(self, obj):
        return obj.created_at.strftime("%y.%m.%d %I:%M%p")
    created_at_short.short_description = "등록일"

    def updated_at_short(self, obj):
        return obj.updated_at.strftime("%y.%m.%d %I:%M%p")
    updated_at_short.short_description = "수정일"


# ✅ 성능 최적화된 가공상품 재고 인라인
class ProductOptionInline(admin.TabularInline):
    model = ProductOption
    extra = 1
    fields = ('external_option_id', 'option_name', 'stock', 'price','calculated_supply' )
    readonly_fields = ('calculated_supply',)

    def calculated_supply(self, obj):
        supply = obj.get_calculated_supply()
        return f"{supply:,.2f} €"
    calculated_supply.short_description = "공급가 (자동계산)"


# ✅ 성능 최적화된 가공상품 관리자
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # ✅ 2번 수정: cart_button을 맨 마지막으로 이동
    list_display = (
        'id', 'retailer', 'brand_name', 'image_tag', 'product_name', 
        'gender', 'category1', 'category2', 'season', 'sku', 'color', 
        'origin_display', 'price_retail', 'discount_rate', 'price_org', 
        'formatted_price_supply', 'markup_display', 'formatted_price_krw', 
        'option_summary', 'material', 'status', 'created_at_short', 'updated_at_short',
        'cart_button'  # ✅ 맨 마지막으로 이동
    )

    search_fields = (
        'product_name', 'brand_name', 'sku', 'color', 'origin'
    )

    inlines = [ProductOptionInline]
    # ✅ 3번 수정: 모든 브랜드 + 수량 표시 필터로 변경
    list_filter = ('retailer', BrandCountListFilter, 'created_at')
    change_list_template = 'admin/shop/product/change_list_with_count.html'
    readonly_fields = ('image_tag',)
    
    # ✅ 페이지네이션 설정 (핵심 최적화)
    list_per_page = 50
    list_max_show_all = 200
    
    # ✅ CSS 추가 - ADD TO CART 우측 고정 (마지막 컬럼) - 수정된 경로
    class Media:
        css = {
            'all': ('admin/css/shop/admin_sticky_cart.css',) if settings.DEBUG else (staticfiles_storage.url('admin/css/shop/admin_sticky_cart.css'),)
        }
    
    # ✅ 쿼리 최적화 - 관련 데이터를 미리 로드
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related(
            'options',  # 옵션 정보
            'cart_set'  # 장바구니 정보 (cart_button에서 사용)
        )

    # 이미지노출
    def image_tag(self, obj):
        if obj.image_url:
            return format_html('''
                <img src="{}" style="width:60px; height:60px; transition: 0.3s;" 
                     onmouseover="this.style.transform='scale(3)'" 
                     onmouseout="this.style.transform='scale(1)'"/>
            ''', obj.image_url)
        return "-"
    image_tag.short_description = '이미지'
    
    # 원화가
    def formatted_price_krw(self, obj):
        if obj.calculated_price_krw is not None:
            return f"{obj.calculated_price_krw:,.0f}"
        return "-"
    formatted_price_krw.short_description = "원화가"

    # 공급가
    def formatted_price_supply(self, obj):
        return f"{obj.price_supply:,.2f}"
    formatted_price_supply.short_description = "공급가"

    # 마크업
    def markup_display(self, obj):
        markup = get_markup_from_product(obj)
        return f"{markup:.2f}" if markup else "-"
    markup_display.short_description = "마크업"
    
    # ✅ 원산지 (select_related 최적화 필요시 추가 가능)
    def origin_display(self, obj):
        try:
            alias = CountryAlias.objects.select_related("standard_country").get(origin_name=obj.origin)
            return f"{obj.origin} (FTA: {'O' if alias.standard_country.fta_applicable else 'X'})"
        except CountryAlias.DoesNotExist:
            return f"{obj.origin} (FTA: X)"
    origin_display.short_description = "원산지 (FTA)"

    # ✅ 옵션재고 (이미 prefetch된 데이터 사용)
    def option_summary(self, obj):
        options = getattr(obj, '_prefetched_objects_cache', {}).get('options')
        if options is None:
            options = list(obj.options.all())

        if not options:
            return "-"

        rows = []
        for opt in options:
            used_qty = opt.cart_quantity + opt.order_quantity
            remaining = int(opt.stock or 0)

            qty_display = format_html(" <span style='color:red;'>(-{})</span>", used_qty) if used_qty > 0 else ""
            soldout_html = format_html(" <strong style='color:gray;'>(재고없음)</strong>") if remaining == 0 else ""

            row = format_html(
                "{}: {}{}{}",
                opt.option_name,
                remaining,
                qty_display,
                soldout_html
            )
            rows.append(row)

        return format_html("<br>".join(rows))
    option_summary.short_description = "재고"
    
    # ✅ 장바구니 버튼 (이미 prefetch된 데이터 사용)
    def cart_button(self, obj):
        carts = getattr(obj, '_prefetched_objects_cache', {}).get('cart_set')
        if carts is None:
            in_cart = Cart.objects.filter(product=obj).exists()
        else:
            in_cart = bool(list(carts))

        if in_cart:
            return format_html(
                '<div style="text-align:center;" class="cart-button-cell">'
                '<span style="font-size:20px;">✅🛒</span><br><br>'
                '<span style="color: green; font-weight: bold;">등록됨</span>'
                '</div>'
            )
        else:
            return format_html(
                '<div style="text-align:center;" class="cart-button-cell">'
                '<a href="/shop/cart/add-product/{}/" style="text-decoration: none;">'
                '<span style="font-size:20px;">➕🛒</span><br><br>'
                '<span style="color: blue; font-weight: bold;">담기</span>'
                '</a></div>', obj.id
            )
    cart_button.short_description = "ADD TO CART"
    
    # ✅ 1번 요청: 날짜 형식 변경 (25.06.05 8:22AM)
    def created_at_short(self, obj):
        return obj.created_at.strftime("%y.%m.%d %I:%M%p")
    created_at_short.short_description = "등록일"
    
    def updated_at_short(self, obj):
        return obj.updated_at.strftime("%y.%m.%d %I:%M%p")
    updated_at_short.short_description = "수정일"


# ✅ 장바구니 주문 생성 액션 (최적화)
@admin.action(description="선택한 상품 주문 생성하기")
def create_order_action(modeladmin, request, queryset):
    # ✅ 관련 데이터를 미리 로드
    queryset = queryset.select_related('product').prefetch_related('options__product_option')
    try:
        orders = create_orders_from_carts(queryset, request)
        messages.success(request, f"{len(orders)}건의 주문이 생성되었습니다.")
    except Exception as e:
        messages.error(request, f"주문 생성 중 오류 발생: {str(e)}")


# ✅ 성능 최적화된 장바구니 관리자
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        'get_retailer', 'get_category', 'get_product_name', 'get_image', 'product_brand',
        'product_price_org', 'product_price_supply', 'product_markup', 'product_price_krw',
        'display_option_table', 'added_at'
    )
    actions = [create_order_action]
    list_filter = ('product__retailer',)
    list_display_links = None
    
    # ✅ 페이지네이션 설정 (핵심 최적화)
    list_per_page = 30
    list_max_show_all = 100
    
    # ✅ 쿼리 최적화 - 모든 관련 데이터를 미리 로드
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related(
            'product'  # Product 테이블 조인
        ).prefetch_related(
            'options__product_option',  # CartOption -> ProductOption 관계
            'product__options'  # Product의 모든 옵션들
        )

    # ✅ JavaScript 파일 경로 수정
    class Media:
        js = ('admin/js/shop/admin_cart.js',) if settings.DEBUG else (staticfiles_storage.url('admin/js/shop/admin_cart.js'),)

    def get_retailer(self, obj):
        return obj.product.retailer
    get_retailer.short_description = "부티크"

    def get_category(self, obj):
        g = obj.product.gender or "-"
        c1 = obj.product.category1 or "-"
        c2 = obj.product.category2
        return f"{g} > {c1} > {c2}" if c2 else f"{g} > {c1}"
    get_category.short_description = "카테고리"

    def get_product_name(self, obj):
        return obj.product.product_name
    get_product_name.short_description = "상품명"

    def get_image(self, obj):
        if obj.product.image_url:
            return format_html(f'<img src="{obj.product.image_url}" width="50" height="50">')
        return "-"
    get_image.short_description = "이미지"

    def product_brand(self, obj):
        return obj.product.brand_name
    product_brand.short_description = "브랜드"

    def product_price_org(self, obj):
        return obj.product.price_org
    product_price_org.short_description = "COST"

    def product_price_supply(self, obj):
        return obj.product.price_supply
    product_price_supply.short_description = "공급가"

    def product_markup(self, obj):
        markup = get_markup_from_product(obj.product)
        return f"{markup:.2f}" if markup else "-"
    product_markup.short_description = "마크업"

    def product_price_krw(self, obj):
        return f"{obj.product.calculated_price_krw:,.0f}" if obj.product.calculated_price_krw else "-"
    product_price_krw.short_description = "원화가"

    # ✅ 옵션 테이블 (이미 prefetch된 데이터 사용)
    def display_option_table(self, obj):
        html = "<table style='border-collapse: collapse;'>"
        html += "<tr><th>OPTION</th><th>재고정보</th><th>COST</th><th>공급가</th><th>ORDER QTY</th></tr>"

        # ✅ prefetch된 데이터 사용 (N+1 쿼리 방지)
        cart_options = getattr(obj, '_prefetched_objects_cache', {}).get('options')
        if cart_options is None:
            cart_options = list(obj.options.all())

        for opt in cart_options:
            option = opt.product_option
            qty = opt.quantity
            stock = option.stock
            cart_qty = option.cart_quantity
            order_qty = option.order_quantity

            # 가격 및 마크업 계산
            markup = get_markup_from_product(obj.product) or 1
            product_price = obj.product.price_supply or 0
            base_price = option.price if option.price is not None else product_price
            supply_price = option.get_calculated_supply()

            price_display = f"{base_price:,.2f} "
            supply_display = f"{supply_price:,.2f}({markup:.2f})"

            html += f"""
            <tr>
                <td>{option.option_name}</td>
                <td>{stock}개 (장바구니: {cart_qty}개, 주문됨: {order_qty}개)</td>
                <td>{price_display}</td>
                <td>{supply_display}</td>
                <td>
                    <input type='number' class='cart-qty-input'
                           data-option-id='{opt.id}'
                           data-max-stock='{stock}'
                           value='{qty}' style='width:40px;' />
                </td>
            </tr>
            """

        html += """
        <tr>
            <td colspan="5" style='text-align: right; padding-top: 8px;'>
                <strong id="cart-total-display">총 주문금액: ₩0</strong><br>
                <button type="button" onclick="saveAllCartOptions()" style="padding: 4px 10px;">💾 전체 저장</button>
            </td>
        </tr>
        </table>
        """
        return format_html(html)
    display_option_table.short_description = "옵션별 주문정보"

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if request.method == 'POST':
            cart = self.get_object(request, object_id)
            for opt in cart.options.all():
                field_name = f'opt_{cart.id}_{opt.product_option.id}'
                if field_name in request.POST:
                    try:
                        opt.quantity = int(request.POST[field_name])
                        opt.save()
                    except ValueError:
                        pass
            self.message_user(request, "주문 수량이 저장되었습니다.", level=messages.SUCCESS)

        return super().change_view(request, object_id, form_url, extra_context)


# ✅ 주문 아이템 인라인 (최적화)
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False

    fields = (
        'retailer_name', 'category', 'brand_name', 'product_name',
        'option_name', 'quantity', 'price_org', 'price_supply' , 'markup', 'price_krw' , 'barcode', 'order_reference' 
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj):
        return False
    
    def retailer_name(self, obj):
        return obj.product.retailer
    
    def category(self, obj):
        return f"{obj.product.category1} > {obj.product.category2}"
    
    def brand_name(self, obj):
        return obj.product.brand_name
    
    def product_name(self, obj):
        return obj.product.product_name
    
    def option_name(self, obj):
        return obj.option.option_name if obj.option else "-"
    
    def quantity(self, obj):
        return obj.quantity
    
    def price_org(self, obj):
        if obj.option and obj.option.price is not None:
            return f"{obj.option.price:,.2f} "
        return f"{obj.product.price_org:,.2f} "

    def price_supply(self, obj):
        if obj.option:
            supply = obj.option.get_calculated_supply()
            return f"{supply:,.2f} €"
        return f"{obj.product.price_supply:,.2f} €"
    
    def markup(self, obj):
        markup = get_markup_from_product(obj.product)
        return f"{markup:.2f}" if markup else "-"
    
    def price_krw(self, obj):
        return obj.price_krw
    
    def barcode(self, obj):
        return obj.option.external_option_id if obj.option else "-"

    def order_reference(self, obj):
        date = obj.order.created_at.strftime("%Y%m%d")
        retailer = obj.order.retailer.code.replace("IT-", "").replace("-", "")
        return f"{date}-ORDER-{obj.order.id}-{obj.id}-{retailer}"

    retailer_name.short_description = "거래처"
    category.short_description = "카테고리"
    brand_name.short_description = "브랜드"
    product_name.short_description = "상품명"
    option_name.short_description = "옵션"
    quantity.short_description = "수량"
    price_org.short_description = "COST"
    price_supply.short_description = "공급가"
    markup.short_description = "브랜드 마크업"
    price_krw.short_description = "주문금액"
    barcode.short_description = "주