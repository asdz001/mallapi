from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from shop.models import CartOption
import json

@csrf_exempt
def save_cart_option(request):
    print("📥 View 도달함 - 요청 감지됨")

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("📦 받은 데이터:", data)

            # ✅ 단일 항목 처리와 복수 항목 처리 구분
            if 'items' in data:
                # 📌 복수 항목 처리
                updated_carts = set()

                for item in data['items']:
                    option_id = item.get('cart_option_id')
                    qty_raw = item.get('quantity')

                    try:
                        qty = int(qty_raw)
                        cart_option = CartOption.objects.get(id=option_id)

                        if cart_option.quantity != qty:
                            cart_option.quantity = qty
                            cart_option.save()
                        
                            cart = cart_option.cart
                            cart.updated_by = request.user
                            cart.save()

                            print(f"✅ 수량 변경됨: option_id={option_id}, quantity={qty}")
                        else:
                            print(f"⏭️ 수량 같음 → 무시: option_id={option_id}")

                    except Exception as e:
                        print(f"❌ 항목 처리 실패: id={option_id}, 에러={e}")
                        continue
   

                return JsonResponse({'success': True})

            else:
                # 📌 기존 방식: 단일 항목 처리
                option_id = data.get('cart_option_id')
                qty = int(data.get('quantity'))

                cart_option = CartOption.objects.get(id=option_id)
                cart_option.quantity = qty
                cart_option.save()

                cart = cart_option.cart
                cart.updated_by = request.user
                cart.save()

                print(f"✅ 저장 성공: option_id={option_id}, quantity={qty}")
                return JsonResponse({'success': True})

        except Exception as e:
            print("❌ 예외 발생:", e)
            return JsonResponse({'success': False, 'error': str(e)})

    print("❌ POST가 아님")
    return JsonResponse({'success': False, 'error': 'Invalid method'})
