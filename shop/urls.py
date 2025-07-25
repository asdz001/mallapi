from django.urls import path
from .admin_views import cart_actions
from .admin_views import admin_import, admin_import ,downloads 


urlpatterns = [
    path("cart/add/<int:option_id>/", cart_actions.add_to_cart, name="add_to_cart"),
    path("cart/add-product/<int:product_id>/", cart_actions.add_to_cart_from_product, name="add_to_cart_from_product"),
    path("admin/api/save-cart-option/", cart_actions.save_cart_option, name="save_cart_option"),
    path("cart-option/order/<int:option_id>/", cart_actions.order_from_cart_option, name="cart-option-order"),
    path('admin/shop/rawproduct/import-excel/', admin_import.import_rawproduct_excel, name='import_rawproduct_excel'),
    path('admin/shop/product/import-excel/', admin_import.import_product_excel, name='import_product_excel'),
    path('admin/shop/rawproduct/export-excel/', admin_import.export_rawproduct_excel,name='export_rawproduct_excel'),
    path("admin/shop/rawproduct/sample-download/", downloads.download_rawproduct_sample, name="download_rawproduct_sample"),

]
