# mall_settings/urls.py

from django.urls import path
from .views.site_settings import site_settings_view
from .views.operator_list import operator_list_view



urlpatterns = [
    path('site/', site_settings_view, name='site_settings'),
    path('operators/', operator_list_view, name='operator_list'),
]
