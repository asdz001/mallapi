# orderreview/models.py

from django.db import models
from shop.models import OrderItem
from pricing.models import Retailer
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
User = get_user_model()


class RetailerUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="유저")
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE, verbose_name="거래처")

    def __str__(self):
        return f"{self.user.username} ({self.retailer.name})"

    class Meta:
        verbose_name = _("거래처 유저")
        verbose_name_plural = _("1. 거래처 유저")


class OrderReview(models.Model):
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, verbose_name="주문 항목")
    retailer = models.ForeignKey(Retailer, on_delete=models.CASCADE, verbose_name="거래처")  # ✅ 명시적으로 저장
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'PENDING - 미확인'),
            ('CONFIRMED', 'CONFIRMED - 확인됨'),
            ('SHIPPED', 'SHIPPED - 출고됨'),
            ('FAILED', 'FAILED - 오류'),
        ],
        default='PENDING',
        verbose_name= _("진행 상태")
    )
    memo = models.TextField(blank=True, null=True, verbose_name=_("비고"))
    last_updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,verbose_name=_("마지막 변경자"))
    last_updated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("마지막 변경시각"))    

    def __str__(self):
        return f"{self.order_item} - {self.status}"

    class Meta:
        verbose_name = _("주문 확인")
        verbose_name_plural = _("2. 거래처 주문확인 목록")

