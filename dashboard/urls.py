# dashboard/urls.py


from django.urls import path
from . import views


app_name = 'dashboard'


urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
]
