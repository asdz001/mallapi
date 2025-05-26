from django.contrib import admin
from .models import Product, Order ,ProductOption  , OrderItem , RawProduct , RawProductOption 
from .models import Cart
from django.contrib import messages
from pricing.models import CountryAlias
from shop.services.order_service import create_orders_from_carts
from django.utils.html import format_html ,format_html_join 
from shop.utils.markup_util import get_markup_from_product
from shop.services.product.conversion_service import convert_or_update_product



#원본상품 재고
class RawProductOptionInline(admin.TabularInline):
    model = RawProductOption
    extra = 1

#원본상품 가공상품으로 전송버튼생성
@admin.action(description="선택한 상품을 가공상품으로 등록/수정")
def convert_selected_raw_products(modeladmin, request, queryset):
    success_count = 0
    fail_count = 0
    for raw_product in queryset:
        if convert_or_update_product(raw_product):
            success_count += 1
        else:
            fail_count += 1
    messages.success(request, f"{success_count}건 등록 성공, {fail_count}건 실패 (로그 확인 필요)")


#원본상품
@admin.register(RawProduct)
class RawProductAdmin(admin.ModelAdmin):
    list_display = ('retailer', 'external_product_id','combined_category', 'image_preview','season', 'raw_brand_name', 'product_name', 'sku',
                      'price_retail','price_org' , 'origin' 'option_summary' ,  'status', 'created_at','updated_at' )

    inlines = [RawProductOptionInline]
    list_filter = ('retailer', 'status', 'created_at')
    search_fields = ('product_name', 'raw_brand_name', 'external_product_id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    actions = [convert_selected_raw_products ]  # ✅ 액션 등록
    change_list_template = 'admin/shop/rawproduct/change_list_with_count.html'


   #카테고리
    def combined_category(self, obj):
        parts = [obj.gender, obj.category1, obj.category2]
        return " > ".join([p for p in parts if p])
    combined_category.short_description = "카테고리"

   #이미지
    def image_preview(self, obj):
        urls = [obj.image_url_1, obj.image_url_2, obj.image_url_3, obj.image_url_3]
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
    
    #재고옵션
    def option_summary(self, obj):
        if not obj.options.exists():
            return "-"
        return format_html("<br>".join(
            f"{opt.option_name} : {opt.stock}" for opt in obj.options.all()
        ))
    

#가공상품 재고
class ProductOptionInline(admin.TabularInline):
    model = ProductOption
    extra = 1

#가공상품
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'retailer', 'brand_name', 'image_tag', 'product_name', 'gender',
        'category1', 'category2', 'season', 'sku', 'color', 'origin_display', 'price_retail',
        'price_org', 'price_supply',  'markup_display' , 'formatted_price_krw' , 'option_summary' , 'material', 'status', 'created_at' , 'updated_at' , 'cart_button'
    )

    list_filter = (
        'retailer', 'brand_name', 'season', 'gender', 'category1', 'status'
    )

    search_fields = (
        'product_name', 'brand_name', 'sku', 'color', 'origin'
    )

    inlines = [ProductOptionInline]

    change_list_template = 'admin/shop/product/change_list_with_count.html'

    readonly_fields = ('image_tag',)

    #이미지노출
    def image_tag(self, obj):
        if obj.image_url:
            return format_html('''
                <img src="{}" style="width:60px; height:60px; transition: 0.3s;" 
                     onmouseover="this.style.transform='scale(3)'" 
                     onmouseout="this.style.transform='scale(1)'"/>
            ''', obj.image_url)
        return "-"
    image_tag.short_description = '이미지'
    
    
    #원화가
    def formatted_price_krw(self, obj):
        if obj.calculated_price_krw is not None:
            return f"{obj.calculated_price_krw:,.0f}"
        return "-"
    formatted_price_krw.short_description = "원화가"


    #마크업
    def markup_display(self, obj):
        markup = get_markup_from_product(obj)
        return f"{markup:.2f}" if markup else "-"
    markup_display.short_description = "마크업"
    
    #원산지
    def origin_display(self, obj):
        try:
            alias = CountryAlias.objects.select_related("standard_country").get(origin_name=obj.origin)
            return f"{obj.origin} (FTA: {'O' if alias.standard_country.fta_applicable else 'X'})"
        except CountryAlias.DoesNotExist:
            return f"{obj.origin} (FTA: X)"
    origin_display.short_description = "원산지 (FTA)"



    #옵션재고
    def option_summary(self, obj):
        options = obj.options.all()
        if not options:
            return "-"

        rows = []
        for opt in options:
            used_qty = opt.cart_quantity + opt.order_quantity
            remaining = int(opt.stock or 0)  # None 방지

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

        # ✅ 줄바꿈을 포함하여 여러 줄로 표시
        return format_html("<br>".join(rows))

    option_summary.short_description = "재고"
    
    
    #장바구니 버튼 추가
    def cart_button(self, obj):
        in_cart = Cart.objects.filter(product=obj).exists()

        # 장바구니에 담긴 상태
        if in_cart:
            # ✅🛒 등록됨
            return format_html(
                '<div style="text-align:center;">'
                '<span style="font-size:20px;">✅🛒</span><br><br>'
                '<span style="color: green; font-weight: bold;">등록됨</span>'
                '</div>'
            )
        else:
            # ➕🛒 담기
            return format_html(
                '<div style="text-align:center;">'
                '<a href="/shop/cart/add-product/{}/" style="text-decoration: none;">'
                '<span style="font-size:20px;">➕🛒</span><br><br>'
                '<span style="color: blue; font-weight: bold;">담기</span>'
                '</a></div>', obj.id
            )

    cart_button.short_description = "ADD TO CART"
    
    #상품등록일
    def created_display(self, obj):
        # KST 기준으로 보기 좋은 포맷
        return obj.created_at.strftime("%Y-%m-%d %H:%M")
    created_display.short_description = "최초 등록일"
    #상품수정일일
    def updated_display(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d %H:%M")
    updated_display.short_description = "최종 수정일"












#장바구니
@admin.action(description="선택한 상품 주문 생성하기")
def create_order_action(modeladmin, request, queryset):
    orders = create_orders_from_carts(queryset, request)
    messages.success(request, f"{len(orders)}건의 주문이 생성되었습니다.")


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

    class Media:
        js = ('shop/admin_cart.js',)
    

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
    product_price_org.short_description = "원가"

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

    def display_option_table(self, obj):
        html = "<table style='border-collapse: collapse;'>"
        html += "<tr><th>OPTION</th><th>재고정보</th><th>ORDER QTY</th></tr>"

        for opt in obj.options.all():
            option = opt.product_option
            stock_text = f"{option.stock}개 (장바구니: {option.cart_quantity}개, 주문됨: {option.order_quantity}개)"
            html += f"""
            <tr>
                <td>{option.option_name}</td>
                <td>{stock_text}</td>
                <td>
                    <input type='number'class='cart-qty-input'data-option-id='{opt.id}'data-max-stock='{option.stock}'value='{opt.quantity}'style='width:40px;' />
                </td>
            </tr>
            """

        # ✅ 이 부분을 추가하세요!
        html += """
        <tr>
            <td colspan="3" style='text-align: right; padding-top: 8px;'>
                <button type="button" onclick="saveAllCartOptions()" style="padding: 4px 10px;">💾 전체 저장</button>
            </td>
        </tr>
        </table>
        """
        return format_html(html)
    

    display_option_table.short_description = "옵션별 주문정보"

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if request.method == 'POST':
            cart = self.get_object(request, object_id)  # 현재 장바구니 객체

            for opt in cart.options.all():  # 이 장바구니에 포함된 옵션들
                field_name = f'opt_{cart.id}_{opt.product_option.id}'  # input의 name 속성과 일치
                if field_name in request.POST:
                    try:
                        opt.quantity = int(request.POST[field_name])
                        opt.save()  # ✅ DB에 저장
                    except ValueError:
                        pass  # 잘못된 값은 무시
            self.message_user(request, "주문 수량이 저장되었습니다.", level=messages.SUCCESS)

        return super().change_view(request, object_id, form_url, extra_context)
    
    
    




#주문
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False

    # ✅ product, option 필드를 안 보이게 하려면 fields에서 제외해야 함
    fields = (
        'retailer_name', 'category', 'brand_name', 'product_name',
        'option_name', 'quantity', 'price_org', 'price_supply' , 'markup', 'price_krw'
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj):
        return False
    #거래처명
    def retailer_name(self, obj):
        return obj.product.retailer
    #카테고리리
    def category(self, obj):
        return f"{obj.product.category1} > {obj.product.category2}"
    #브랜드명
    def brand_name(self, obj):
        return obj.product.brand_name
    #상품명
    def product_name(self, obj):
        return obj.product.product_name
    #옵션명
    def option_name(self, obj):
        return obj.option.option_name
    #주문수량
    def quantity(self, obj):
        return obj.quantity
    #원가가
    def price_org(self, obj):
        return obj.product.price_org
    #공급가
    def price_supply(self, obj):
        return obj.product.price_supply
    
    #마크업
    def markup(self, obj):
        markup = get_markup_from_product(obj.product)
        return f"{markup:.2f}" if markup else "-"
    #원화
    def price_krw(self, obj):
        return obj.price_krw

    retailer_name.short_description = "거래처"
    category.short_description = "카테고리"
    brand_name.short_description = "브랜드"
    product_name.short_description = "상품명"
    option_name.short_description = "옵션"
    quantity.short_description = "수량"
    price_org.short_description = "원가"
    price_supply.short_description = "공급가"
    markup.short_description = "브랜드 마크업"
    price_krw.short_description = "주문금액"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'retailer', 'status', 'order_summary' , 'created_at')
    list_filter = ('retailer', 'status')
    readonly_fields = ('created_at',)
    inlines = [OrderItemInline]


    def order_summary(self, obj):
        try:
            items = obj.items.all()

            total_qty = 0
            total_supply = 0
            total_krw = 0

            for item in items:
                qty = int(item.quantity or 0)
                supply = int(item.product.price_supply or 0)
                krw = int(item.price_krw or 0)

                total_qty += qty
                total_supply += qty * supply
                total_krw += qty * krw

            return format_html(
                "<strong>총 수량:</strong> {}개<br>"
                "<strong>총 공급가:</strong> {} €<br>"
                "<strong>총 원화가:</strong> {}원",
                f"{total_qty:,}",
                f"{total_supply:,}",
                f"{total_krw:,}"
            )

        except Exception as e:
            return format_html("<span style='color:red;'>오류 발생: {}</span>", e)

    order_summary.short_description = "주문 요약"






