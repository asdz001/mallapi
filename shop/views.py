from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse , HttpResponse
from shop.models import Product, ProductOption, Cart, CartOption
from django.contrib import messages
from shop.services.order_service import create_orders_from_carts
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt


def my_view(request):
    return HttpResponse("Hello from my_view!")




# ✅ 장바구니: 옵션 ID로 직접 담기
def add_to_cart(request, option_id):
    option = get_object_or_404(ProductOption, id=option_id)
    quantity = int(request.POST.get('quantity', 1))

    cart_item, created = Cart.objects.get_or_create(product_option=option)
    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()

    return JsonResponse({"message": "장바구니에 담겼습니다."})


# ✅ 장바구니 : 상품 ID로 전체 옵션 초기 세팅
def add_to_cart_from_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if not product.options.exists():
        messages.error(request, "해당 상품에 옵션이 없습니다.")
        return redirect("/admin/shop/product/")

    cart = Cart.objects.create(
        product=product,
        created_by=request.user,
    )

    has_valid_option = False
    for option in product.options.all():
        if option.stock > 0:
            CartOption.objects.create(cart=cart, product_option=option, quantity=0)
            has_valid_option = True

    if not has_valid_option:
        cart.delete()
        messages.error(request, "재고가 있는 옵션이 없습니다.")
        return redirect("/admin/shop/product/")
    
    

    return redirect("/admin/shop/cart/")




#장바구니
def add_to_cart(request, option_id):
    option = get_object_or_404(ProductOption, id=option_id)
    quantity = int(request.POST.get('quantity', 1))

    # 이미 담긴 항목은 수량 증가
    cart_item, created = Cart.objects.get_or_create(product_option=option)
    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()

    return JsonResponse({"message": "장바구니에 담겼습니다."})



@csrf_exempt
@require_POST
def order_from_cart_option(request, option_id):
    print(f"📥 View 도달: 주문 요청 받음, option_id={option_id}")

    cart_option = get_object_or_404(CartOption, id=option_id)

    print(f"🧾 현재 수량: {cart_option.quantity}, 상태: {cart_option.order_status}, 마지막 전송 수량: {cart_option.last_sent_quantity}")

    if cart_option.quantity <= 0:
        print("❌ 수량 0이라 주문 거절")
        return JsonResponse({"error": "❌ 수량 없음"}, status=400)

    cart_option.order_status = "SENT"
    cart_option.last_sent_quantity = cart_option.quantity
    cart_option.order_message = f"수동 주문 처리됨 - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
    cart_option.save(update_fields=["order_status", "last_sent_quantity", "order_message"])

    print("✅ 주문 상태 저장 완료")
    return JsonResponse({"status": "ok"})
