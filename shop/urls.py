from django.urls import path
from . import views
from shop.views_admin import save_cart_option
from shop.views import order_from_cart_option

urlpatterns = [
    path('my/', views.my_view),
    path('cart/add/<int:option_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/add-product/<int:product_id>/', views.add_to_cart_from_product, name='add_to_cart_from_product'),
    path('admin/api/save-cart-option/', save_cart_option, name='save_cart_option'),
    path("cart-option/order/<int:option_id>/", order_from_cart_option, name="cart-option-order"),

]
