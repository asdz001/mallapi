from django.core.management.base import BaseCommand
from shop.models import Order, OrderDashboard


class Command(BaseCommand):
    help = '기존 주문들을 OrderDashboard에 연동합니다'

    def handle(self, *args, **options):
        # 기존 주문 중 OrderDashboard가 없는 것들 찾기
        orders_without_dashboard = Order.objects.filter(dashboard__isnull=True)
        
        created_count = 0
        
        for order in orders_without_dashboard:
            # 주문 요약 정보 계산
            items = order.items.all()
            total_qty = sum(item.quantity for item in items)
            total_amount_krw = sum(item.quantity * (item.price_krw or 0) for item in items)
            
            order_summary = {
                'total_quantity': total_qty,
                'total_amount_krw': total_amount_krw,
                'item_count': items.count(),
            }
            
            # OrderDashboard 생성
            dashboard = OrderDashboard.objects.create(
                order=order,
                retailer=order.retailer,
                order_summary=order_summary
            )
            
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'주문 #{order.id} → 대시보드 #{dashboard.id} 생성 완료'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n총 {created_count}개의 OrderDashboard가 생성되었습니다!'
            )
        )
