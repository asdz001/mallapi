from django.db import models
from pricing.models import Retailer
from shop.services.price_calculator import apply_price_to_product
from dictionary.models import BrandAlias
from shop.utils.markup_util import get_markup_from_product
from decimal import Decimal
from shop.services.price_calculator import calculate_final_price
from django.utils.translation import gettext_lazy as _  # 이미 있음
from django.contrib.auth.models import User

# 🔧 브랜드 자동 치환 함수
def resolve_standard_brand(raw_name):
    alias = BrandAlias.objects.filter(alias__iexact=raw_name).select_related('brand').first()
    return alias.brand.name if alias else "-"

# ✅ 원본 상품 모델 (완성형)
class RawProduct(models.Model):
    retailer = models.CharField(max_length=100, verbose_name=_("부띠끄명"))
    external_product_id = models.CharField(_("고유상품 ID"), max_length=100, null=True, blank=True, db_index=True)
    raw_brand_name = models.CharField(max_length=100, verbose_name=_("원본 브랜드명"), null=True, blank=True)
    product_name = models.CharField(max_length=255, verbose_name=_("상품명"))
    gender = models.CharField(max_length=10, verbose_name=_("성별"), blank=True, null=True)
    category1 = models.CharField(max_length=100, verbose_name=_("카테고리1"), blank=True, null=True)
    category2 = models.CharField(max_length=100, verbose_name=_("카테고리2"), blank=True, null=True)
    season = models.CharField(max_length=50, verbose_name=_("시즌"), blank=True, null=True)
    sku = models.CharField(max_length=100, verbose_name=_("SKU"), blank=True, null=True)
    color = models.CharField(max_length=50, verbose_name=_("색상명"), blank=True, null=True)
    origin = models.CharField(max_length=100, verbose_name=_("원산지"), blank=True, null=True)
    material = models.CharField(max_length=255, verbose_name=_("소재"), blank=True, null=True)
    image_url_1 = models.URLField(verbose_name=_("이미지 URL 1"), blank=True, null=True)
    image_url_2 = models.URLField(verbose_name=_("이미지 URL 2"), blank=True, null=True)
    image_url_3 = models.URLField(verbose_name=_("이미지 URL 3"), blank=True, null=True)
    image_url_4 = models.URLField(verbose_name=_("이미지 URL 3"), blank=True, null=True)
    price_org = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("COST"), default=0)
    price_supply = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("판매가"), default=0)
    discount_rate = models.DecimalField(_("할인율 (%)"), max_digits=5, decimal_places=2, null=True, blank=True)
    price_retail = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("소비자가"), default=0)
    description = models.TextField(blank=True, null=True, verbose_name="설명")
    status = models.CharField(
        max_length=10,
        choices=[('pending', _("미등록")), ('converted', _("등록됨")), ('soldout', _("품절됨")) ],
        default='pending',
        verbose_name=_("상태")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("수집일"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("수정일"))

    class Meta:
        verbose_name = _("상품원본")
        verbose_name_plural = _("1. 상품원본 목록")

#원본상품의 재고
class RawProductOption(models.Model):
    product = models.ForeignKey('shop.RawProduct', on_delete=models.CASCADE, related_name='options')
    external_option_id = models.CharField(_("외부 옵션 ID"), max_length=100, null=True, blank=True, db_index=True)
    option_name = models.CharField(max_length=100, verbose_name=_("옵션명"))
    stock = models.IntegerField(default=0, verbose_name=_("재고 수량"))
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("옵션 가격"), null=True, blank=True)  # ✅ 추가

    def save(self, *args, **kwargs):
        if self.option_name:
            self.option_name = self.option_name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.product_name} - {self.option_name} ({self.stock})"

    class Meta:
        verbose_name = _("원본 옵션")
        verbose_name_plural = _("1-1. 원본 옵션 목록")

#상품정보
class Product(models.Model):
    retailer = models.CharField(max_length=100, verbose_name=_("부띠끄명"))
    external_product_id = models.CharField(_("고유상품 ID"), max_length=100, null=True, blank=True, db_index=True, unique=True)
    brand_name = models.CharField(max_length=100, verbose_name=_("브랜드명"), null=True, blank=True ) 
    raw_brand_name = models.CharField(max_length=100, verbose_name=_("원본 브랜드명"), null=True, blank=True ) 
    image_url = models.URLField(verbose_name=_("이미지 URL"), blank=True, null=True)
    product_name = models.CharField(max_length=255, verbose_name=_("상품명"))
    gender = models.CharField(max_length=10, verbose_name=_("성별"), blank=True, null=True)
    category1 = models.CharField(max_length=100, verbose_name=_("카테고리1"), blank=True, null=True)
    category2 = models.CharField(max_length=100, verbose_name=_("카테고리2"), blank=True, null=True)
    season = models.CharField(max_length=50, verbose_name=_("시즌"), blank=True, null=True)
    sku = models.CharField(max_length=100, verbose_name=_("SKU"), blank=True, null=True)
    color = models.CharField(max_length=50, verbose_name=_("색상명"), blank=True, null=True)
    origin = models.CharField(max_length=100, verbose_name=_("원산지"), blank=True, null=True)
    price_org = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("COST"), default=0)
    price_supply = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("공급가"), default=0)
    discount_rate = models.DecimalField(_("할인율 (%)"), max_digits=5, decimal_places=2, null=True, blank=True)
    price_retail = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("소비자가"), default=0)
    calculated_price_krw = models.DecimalField(_("원화가"), max_digits=12, decimal_places=0, null=True, blank=True)
    material = models.CharField(max_length=255, verbose_name=_("소재"), blank=True, null=True)
    description = models.TextField(blank=True, null=True, verbose_name="설명")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("최초 등록일"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("수정일"))

    STATUS_CHOICES = [
        ('pending', _("미등록")),
        ('active', _("등록됨")),
        ('soldout', _("품절됨")),     
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name=_("상태"))

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
    image_tag.short_description = _("이미지")

    class Meta:
        verbose_name = _("상품")
        verbose_name_plural = _("2. 가공상품")

#옵션별 재고
class ProductOption(models.Model):
    external_option_id = models.CharField(_("외부 옵션 ID"), max_length=100, null=True, blank=True, db_index=True)
    product = models.ForeignKey('shop.Product', on_delete=models.CASCADE, related_name='options')
    option_name = models.CharField(max_length=100, verbose_name=_("옵션명"))
    stock = models.IntegerField(default=0, verbose_name=_("재고 수량"))
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("옵션 COST"), null=True, blank=True)  # ✅ 추가

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
    product = models.ForeignKey('shop.Product', on_delete=models.CASCADE, verbose_name=_("상품"))
    added_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_%(class)s")
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_%(class)s")

    def __str__(self):
        return f"{self.product.product_name}"

    class Meta:
        verbose_name = _("장바구니")
        verbose_name_plural = _("3. 장바구니")

# 옵션 단위 수량 정보
class CartOption(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='options')
    product_option = models.ForeignKey('shop.ProductOption', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.cart.product.product_name} - {self.product_option.option_name}: {self.quantity}개"

#주문내역    
class Order(models.Model):
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE, verbose_name=_("거래처"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("주문일시"))
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_%(class)s")
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_%(class)s")

    STATUS_CHOICES = [
        ("PENDING", _("대기중")),
        ("SENT", _("전송됨")),
        ("COMPLETED", _("완료")),
        ("FAILED", _("전송실패")),
        ("SOIDOUT", _("품절취소")),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", verbose_name=_("상태"))
    memo = models.TextField(blank=True, null=True, verbose_name=_("관리자 메모"))

    def __str__(self):
        return f"주문 #{self.id} - {self.retailer.name}"
    
    class Meta:
        verbose_name = _("주문내역")
        verbose_name_plural = _("4. 주문내역")

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    option = models.ForeignKey(ProductOption, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_krw = models.DecimalField(_("원화가"), max_digits=12, decimal_places=0, null=True, blank=True)
    external_order_number = models.CharField(max_length=100,blank=True,null=True,verbose_name="	order_number(날짜-고유번호-업체명)" )  # 관리자 페이지 표시 이름

    def __str__(self):
        try:
            date = self.order.created_at.strftime("%Y%m%d")
            retailer = self.order.retailer.code.replace("IT-", "").replace("-", "")
            product_name = self.product.product_name if self.product else "-"
            option_name = self.option.option_name if self.option else "-"
            qty = self.quantity
            return f"{date}-ORDER-{self.order.id}-{self.id}-{retailer} | {product_name} | {option_name} | x {qty}개"
        except Exception:
            return f"OrderItem #{self.id}"
        


    ORDER_STATUS_CHOICES = [
        ("SENT", "전송 완료"),
        ("FAILED", "전송 실패"),
    ]

    order_status = models.CharField(
        max_length=10,
        choices=ORDER_STATUS_CHOICES,
        blank=True,
        null=True,
        verbose_name="주문 전송 상태"
    )
    order_message = models.TextField(
        blank=True,
        null=True,
        verbose_name="주문 전송 메시지 (실패 사유 등)"
    )        




