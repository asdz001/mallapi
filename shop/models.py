from django.db import models
from pricing.models import Retailer
from shop.services.price_calculator import apply_price_to_product
from dictionary.models import BrandAlias
from shop.utils.markup_util import get_markup_from_product
from decimal import Decimal
from shop.services.price_calculator import calculate_final_price




# 🔧 브랜드 자동 치환 함수
def resolve_standard_brand(raw_name):
    alias = BrandAlias.objects.filter(alias__iexact=raw_name).select_related('brand').first()
    return alias.brand.name if alias else "-"

# ✅ 원본 상품 모델 (완성형)
class RawProduct(models.Model):
    retailer = models.CharField(max_length=100, verbose_name="부띠끄명")
    external_product_id = models.CharField("고유상품 ID", max_length=100, null=True, blank=True, db_index=True)
    raw_brand_name = models.CharField(max_length=100, verbose_name="원본 브랜드명", null=True, blank=True)
    product_name = models.CharField(max_length=255, verbose_name="상품명")
    gender = models.CharField(max_length=10, verbose_name="성별", blank=True, null=True)
    category1 = models.CharField(max_length=100, verbose_name="카테고리1", blank=True, null=True)
    category2 = models.CharField(max_length=100, verbose_name="카테고리2", blank=True, null=True)
    season = models.CharField(max_length=50, verbose_name="시즌", blank=True, null=True)
    sku = models.CharField(max_length=100, verbose_name="SKU", blank=True, null=True)
    color = models.CharField(max_length=50, verbose_name="색상명", blank=True, null=True)
    origin = models.CharField(max_length=100, verbose_name="원산지", blank=True, null=True)
    material = models.CharField(max_length=255, verbose_name="소재", blank=True, null=True)
    image_url_1 = models.URLField(verbose_name="이미지 URL 1", blank=True, null=True)
    image_url_2 = models.URLField(verbose_name="이미지 URL 2", blank=True, null=True)
    image_url_3 = models.URLField(verbose_name="이미지 URL 3", blank=True, null=True)
    image_url_4 = models.URLField(verbose_name="이미지 URL 3", blank=True, null=True)
    price_org = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="COST", default=0)
    price_supply = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="판매가", default=0)
    discount_rate = models.DecimalField("할인율 (%)", max_digits=5, decimal_places=2, null=True, blank=True)
    price_retail = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="소비자가", default=0)
    status = models.CharField(max_length=10, choices=[('pending', '미등록'), ('converted', '등록됨')], default='pending', verbose_name="상태")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="수집일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")


    class Meta:
        verbose_name = "상품원본"
        verbose_name_plural = "1. 상품원본 목록"


#원본상품의 재고
class RawProductOption(models.Model):
    product = models.ForeignKey('shop.RawProduct', on_delete=models.CASCADE, related_name='options')
    external_option_id = models.CharField("외부 옵션 ID", max_length=100, null=True, blank=True, db_index=True)
    option_name = models.CharField(max_length=100, verbose_name="옵션명")
    stock = models.IntegerField(default=0, verbose_name="재고 수량")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="옵션 가격", null=True, blank=True)  # ✅ 추가

    def save(self, *args, **kwargs):
        if self.option_name:
            self.option_name = self.option_name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.product_name} - {self.option_name} ({self.stock})"

    class Meta:
        verbose_name = "원본 옵션"
        verbose_name_plural = "1-1. 원본 옵션 목록"



#상품정보
class Product(models.Model):


    retailer = models.CharField(max_length=100, verbose_name="부띠끄명")
    external_product_id = models.CharField("고유상품 ID", max_length=100, null=True, blank=True, db_index=True, unique=True)
    brand_name = models.CharField(max_length=100, verbose_name="브랜드명", null=True, blank=True ) 
    raw_brand_name = models.CharField(max_length=100, verbose_name="원본 브랜드명", null=True, blank=True ) 
    image_url = models.URLField(verbose_name="이미지 URL", blank=True, null=True)
    product_name = models.CharField(max_length=255, verbose_name="상품명")
    gender = models.CharField(max_length=10, verbose_name="성별", blank=True, null=True)
    category1 = models.CharField(max_length=100, verbose_name="카테고리1", blank=True, null=True)
    category2 = models.CharField(max_length=100, verbose_name="카테고리2", blank=True, null=True)
    season = models.CharField(max_length=50, verbose_name="시즌", blank=True, null=True)
    sku = models.CharField(max_length=100, verbose_name="SKU", blank=True, null=True)
    color = models.CharField(max_length=50, verbose_name="색상명", blank=True, null=True)
    origin = models.CharField(max_length=100, verbose_name="원산지", blank=True, null=True)
    price_org = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="COST", default=0)
    price_supply = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="공급가", default=0)
    discount_rate = models.DecimalField("할인율 (%)", max_digits=5, decimal_places=2, null=True, blank=True)
    price_retail = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="소비자가", default=0)
    calculated_price_krw = models.DecimalField("원화가", max_digits=12, decimal_places=0, null=True, blank=True)
    material = models.CharField(max_length=255, verbose_name="소재", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="최초 등록일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    STATUS_CHOICES = [
        ('pending', '미등록'),
        ('active', '등록됨'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="상태")

    #공급가 계산
    @property
    def price_supply(self):
        if not self.price_org:
            return None
        markup = get_markup_from_product(self) or 1
        return self.price_org * Decimal(str(markup))
    
    #원화 계산
    @property
    def calculated_price_krw(self):
        return calculate_final_price(self)

    #상품명
    def __str__(self):
        return f"[{self.retailer}] {self.brand_name} - {self.product_name}"

    #이미지
    def image_tag(self):
        if self.image_url:
            return f'<img src="{self.image_url}" width="50" height="50" />'
        return "-"
    image_tag.allow_tags = True
    image_tag.short_description = '이미지'



    class Meta:
        verbose_name = "상품"
        verbose_name_plural = "2. 가공상품"




#옵션별 재고
class ProductOption(models.Model):
    external_option_id = models.CharField("외부 옵션 ID", max_length=100, null=True, blank=True, db_index=True)
    product = models.ForeignKey('shop.Product', on_delete=models.CASCADE, related_name='options')
    option_name = models.CharField(max_length=100, verbose_name="옵션명")
    stock = models.IntegerField(default=0, verbose_name="재고 수량")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="옵션 COST", null=True, blank=True)  # ✅ 추가

    def save(self, *args, **kwargs):
        if self.option_name:
            self.option_name = self.option_name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.product_name} - {self.option_name} ({self.stock})"
    
    
        #장바구니 담긴 상품수
    @property
    def cart_quantity(self):
        return sum(opt.quantity for opt in self.cartoption_set.all())
    #주문내역 상품수
    @property
    def order_quantity(self):
        return sum(item.quantity for item in self.orderitem_set.all())
    
    #옵션별 가격 - 마크업 포함
    def get_calculated_supply(self):
        from shop.utils.markup_util import get_markup_from_product
        from decimal import Decimal

        if self.price is not None:
            markup = get_markup_from_product(self.product) or 1
            return self.price * Decimal(str(markup))
        return self.product.price_supply or 0

    
    



#장바구니(주문하기)
class Cart(models.Model):
    product = models.ForeignKey('shop.Product', on_delete=models.CASCADE, verbose_name="상품")
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.product_name}"


    class Meta:
        verbose_name = "장바구니"
        verbose_name_plural = "3. 장바구니"



# 옵션 단위 수량 정보
class CartOption(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='options')
    product_option = models.ForeignKey('shop.ProductOption', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.cart.product.product_name} - {self.product_option.option_name}: {self.quantity}개"







#주문내역    
class Order(models.Model):
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE, verbose_name="거래처")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="주문일시")

    STATUS_CHOICES = [
        ("PENDING", "대기중"),
        ("SENT", "전송됨"),
        ("COMPLETED", "완료"),
        ("FAILED", "전송실패"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", verbose_name="상태")
    memo = models.TextField(blank=True, null=True, verbose_name="관리자 메모")

    def __str__(self):
        return f"주문 #{self.id} - {self.retailer.name}"
    

    class Meta:
        verbose_name = "주문내역"
        verbose_name_plural = "4. 주문내역"



class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    option = models.ForeignKey(ProductOption, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_krw = models.DecimalField("원화가", max_digits=12, decimal_places=0, null=True, blank=True)

    def __str__(self):
        return f"{self.product.product_name} - {self.option.option_name} x {self.quantity}개"


# ✅ 주문 대시보드 모델 추가
class OrderDashboard(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, verbose_name="주문", related_name="dashboard")
    order_reference = models.CharField(max_length=100, unique=True, verbose_name="주문번호", db_index=True)
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE, verbose_name="거래처")
    
    # 주문 요약 정보 (JSON으로 저장)
    order_summary = models.JSONField(verbose_name="주문 요약", help_text="상품수, 총금액 등")
    
    # 거래처별 상태 관리
    partner_status = models.CharField(
        max_length=20, 
        choices=[
            ("PENDING", "확인대기"),
            ("CONFIRMED", "확인완료"), 
            ("PROCESSING", "처리중"),
            ("SHIPPED", "배송중"),
            ("DELIVERED", "배송완료"),
            ("CANCELLED", "취소됨"),
        ],
        default="PENDING",
        verbose_name="거래처 상태"
    )
    
    # 자동 추천번호 생성 필드
    auto_order_number = models.CharField(max_length=50, verbose_name="자동주문번호", help_text="20250605-ORDER-123-IT-CUCCINI")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    def save(self, *args, **kwargs):
        if not self.order_reference:
            # 주문번호 자동 생성: 날짜-ORDER-ID-거래처코드
            date_str = self.order.created_at.strftime("%Y%m%d")
            retailer_code = self.retailer.code.replace("IT-", "").replace("-", "")
            self.order_reference = f"{date_str}-ORDER-{self.order.id}-{retailer_code}"
            
        if not self.auto_order_number:
            # 자동 추천번호 생성
            date_str = self.order.created_at.strftime("%Y%m%d")
            retailer_code = self.retailer.code.replace("IT-", "").replace("-", "")
            self.auto_order_number = f"{date_str}-ORDER-{self.order.id}-{retailer_code}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"대시보드 - {self.order_reference}"

    class Meta:
        verbose_name = "주문 대시보드"
        verbose_name_plural = "5. 주문 대시보드"


