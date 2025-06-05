# shop/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, OrderDashboard

@receiver(post_save, sender=Order)
def create_order_dashboard(sender, instance, created, **kwargs):
    """주문 생성 시 자동으로 OrderDashboard 생성"""
    if created:
        # 주문 요약 정보 계산
        items = instance.items.all()
        total_qty = sum(item.quantity for item in items)
        total_amount_krw = sum(item.quantity * (item.price_krw or 0) for item in items)
        
        order_summary = {
            'total_quantity': total_qty,
            'total_amount_krw': total_amount_krw,
            'item_count': items.count(),
        }
        
        # OrderDashboard 생성
        OrderDashboard.objects.create(
            order=instance,
            retailer=instance.retailer,
            order_summary=order_summary
        )
