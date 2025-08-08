# mall_settings/urls.py

from django.urls import path
from .views.site_settings import site_settings_view
from .views.operator_list import operator_list_view
from .views.operator_crud import operator_create_view,operator_update_view,operator_delete_view,operator_detail_view

urlpatterns = [
    path('site/', site_settings_view, name='site_settings'),
    path('operators/', operator_list_view, name='operator_list'),
    path('operators/create/', operator_create_view, name='operator_create'),
    path('operators/<int:pk>/edit/', operator_update_view, name='operator_update'),
    path('operators/<int:pk>/delete/', operator_delete_view, name='operator_delete'),
    path('operators/<int:pk>/detail/', operator_detail_view, name='operator_detail'),
]
