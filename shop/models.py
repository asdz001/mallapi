from django.db import models
from pricing.models import Retailer
from shop.services.price_calculator import apply_price_to_product
from dictionary.models import BrandAlias
from shop.utils.markup_util import get_markup_from_product
from decimal import Decimal
from shop.services.price_calculator import calculate_final_price
from django.contrib.auth.models import User




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




# ✅ 새로운 OrderDashboard 모델 - 거래처 주문 관리용
class OrderDashboard(models.Model):
    """주문 대시보드 - 거래처 확인용"""
    
    # 주문 연결
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='dashboard')
    
    # 기본 정보
    date = models.DateField("주문일", auto_now_add=True)
    tracking_number = models.CharField("운송장번호", max_length=50, unique=True)
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE, verbose_name="거래처")
    
    # 주문 상품 요약 정보 (JSON으로 저장 - 구글시트 형태)
    order_summary = models.JSONField("주문요약", default=dict, help_text="주문 상품 요약 정보")
    
    # 상태 관리
    STATUS_CHOICES = [
        ('PENDING', '확인중'),
        ('APPROVED', '주문가능'),
        ('REJECTED', '주문불가'),
        ('SHIPPED', '배송완료')
    ]
    status = models.CharField("상태", max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # 메타 정보
    updated_by = models.CharField("확인자", max_length=100, blank=True)
    updated_at = models.DateTimeField("확인일시", auto_now=True)
    rejection_reason = models.TextField("거부 사유", blank=True)
    notes = models.TextField("비고", blank=True)
    
    # 거래처 알림 관련
    notified_at = models.DateTimeField("알림일시", null=True, blank=True)
    notification_sent = models.BooleanField("알림전송여부", default=False)
    
    class Meta:
        verbose_name = "주문 대시보드"
        verbose_name_plural = "5. 주문 대시보드"
        ordering = ['-date', '-id']
    
    def __str__(self):
        return f"{self.tracking_number} - {self.retailer.name} ({self.get_status_display()})"
    
    @classmethod
    def create_from_order(cls, order):
        """주문 생성 시 자동으로 대시보드 항목 생성"""
        tracking_number = f"{order.created_at.strftime('%Y%m%d')}-ORDER-{order.id}-{order.retailer.code}"
        
        # 주문 상품 요약 정보 생성 (구글시트 형태)
        order_summary = {
            "milanese_order_id": f"4e964b4c-f924-440d-a75d-77a4a636b7b_{order.id}",
            "total_amount": 0,
            "total_quantity": 0,
            "brands": [],
            "products": []
        }
        
        # 주문 아이템들로부터 요약 정보 생성
        total_amount = 0
        total_quantity = 0
        brands = set()
        products = []
        
        for item in order.items.all():
            total_quantity += item.quantity
            item_amount = float(item.price_krw or 0) * item.quantity
            total_amount += item_amount
            
            brands.add(item.product.brand_name)
            products.append({
                "product_id": item.product.external_product_id or f"PROD_{item.product.id}",
                "brand": item.product.brand_name,
                "size": item.option.option_name,
                "quantity": item.quantity,
                "amount": item_amount
            })
        
        order_summary.update({
            "total_amount": total_amount,
            "total_quantity": total_quantity,
            "brands": list(brands),
            "products": products
        })
        
        return cls.objects.create(
            order=order,
            retailer=order.retailer,
            tracking_number=tracking_number,
            order_summary=order_summary
        )
    
    def get_order_items_display(self):
        """주문 상품 목록을 구글시트 형태로 반환"""
        items = []
        for product in self.order_summary.get('products', []):
            items.append({
                'Date': self.date.strftime('%d.%m.%y'),
                'Tracking Number': self.tracking_number,
                'Milanese Korea Order #': self.order_summary.get('milanese_order_id', ''),
                'BRANDS': product.get('brand', ''),
                'Product ID': product.get('product_id', ''),
                'Size': product.get('size', ''),
                'Qty': product.get('quantity', 0),
                'Amount': product.get('amount', 0),
            })
        return items


# ✅ 거래처 사용자 모델 - 권한 관리용
class PartnerUser(models.Model):
    """거래처 담당자 계정"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE, verbose_name="담당 거래처")
    is_active = models.BooleanField("활성 상태", default=True)
    phone = models.CharField("연락처", max_length=20, blank=True)
    department = models.CharField("부서", max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "거래처 사용자"
        verbose_name_plural = "거래처 사용자 목록"
    
    def __str__(self):
        return f"{self.user.username} - {self.retailer.name}"




# ✅ 시그널 추가 - 주문 생성 시 자동으로 대시보드 생성
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Order)
def create_order_dashboard(sender, instance, created, **kwargs):
    """주문 생성 시 자동으로 대시보드 항목 생성"""
    if created:
        try:
            OrderDashboard.create_from_order(instance)
        except Exception as e:
            # 로그 기록 (실제 환경에서는 logger 사용)
            print(f"OrderDashboard 생성 실패: {e}")
