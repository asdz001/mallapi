from django.shortcuts import render
from shop.models import Product
from django.core.paginator import Paginator



# 대시보드 홈
def dashboard_home(request):
    return render(request, 'dashboard/home.html')


#상품리스트
def product_list(request):
    query = request.GET.get('q', '')
    page = request.GET.get('page', 1)
    per_page = int(request.GET.get('per_page', 20))  # ✅ 기본은 20

    products_qs = Product.objects.all().order_by('-created_at')
    if query:
        products_qs = products_qs.filter(name__icontains=query)

    paginator = Paginator(products_qs, per_page)
    products = paginator.get_page(page)
    per_page_options = [20, 100, 500, 1000]

    return render(request, 'dashboard/product_list.html', {
        'products': products,
        'query': query,
        'per_page': per_page,
        'page': page,
        'per_page_options': per_page_options,
    })

# 상품 추가 페이지
def product_add(request):
    return render(request, 'dashboard/product_add.html')
