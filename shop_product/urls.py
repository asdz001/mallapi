# shop_product/urls.py

from django.urls import path
from shop_product.views.classification import supplier, category , origin , brand
from shop_product.views.product import product_add, product_list # ✅ category 추가


urlpatterns = [
    # 상품 목록 및 관리
    path('', product_list.product_list, name='product_list'),
    path('add', product_add.product_add, name='product_add'),
    
    # 🆕 컬럼 설정 관련 URL 추가
    path('column-settings/save/', product_list.save_column_settings, name='save_column_settings'),
    path('column-settings/get/', product_list.get_column_settings, name='get_column_settings'),
    
    


    

    
# 🔧 거래처 관리 URL 패턴
    path('classification/supplier/', supplier.supplier_list, name='supplier_list'),
    path('classification/supplier/create/', supplier.supplier_create, name='supplier_create'),
    path('classification/supplier/<int:supplier_id>/detail/', supplier.supplier_detail, name='supplier_detail'),
    path('classification/supplier/<int:supplier_id>/update/', supplier.supplier_update, name='supplier_update'),
    path('classification/supplier/<int:supplier_id>/delete/', supplier.supplier_delete, name='supplier_delete'),
    
# 🔧 카테고리 관리 URL 패턴    
    # ✅ 카테고리 관리 URL 패턴 (누락된 것만 추가)
    path('classification/category/', category.category_list, name='category_list'),
    path('classification/category/create/', category.category_create, name='category_create'),
    path('classification/category/<str:level>/<int:category_id>/detail/', category.category_detail, name='category_detail'),
    path('classification/category/<str:level>/<int:category_id>/update/', category.category_update, name='category_update'),
    path('classification/category/<str:level>/<int:category_id>/delete/', category.category_delete, name='category_delete'),
    path('classification/category/quick_create/', category.category_quick_create, name='category_quick_create'),

    # ✅ 카테고리 “옵션” API (이 한 줄이 필요합니다)
    path('classification/category/options/<str:level>/', category.category_options, name='category_options'),
    

# 🔧 카테고리 옵션 관리
    # 🔧 기타 분류 관리 (추후 구현)
    path('classification/origin/', origin.origin_list, name='origin_list'),
    path('classification/origin/countries/', origin.get_country_options, name='origin_country_options'),  # 🆕 추가
    
    # 📊 표준국가 관리
    path('classification/origin/country/create/', origin.country_create, name='origin_country_create'),
    path('classification/origin/country/<int:country_id>/detail/', origin.country_detail, name='origin_country_detail'),
    path('classification/origin/country/<int:country_id>/update/', origin.country_update, name='origin_country_update'),
    path('classification/origin/country/<int:country_id>/delete/', origin.country_delete, name='origin_country_delete'),

    # 🔗 별칭 관리
    path('classification/origin/alias/create/', origin.alias_create, name='origin_alias_create'),
    path('classification/origin/alias/<int:alias_id>/delete/', origin.alias_delete, name='origin_alias_delete'),







# 🔧 브랜드 관리 URL 패턴
    path('classification/brand/', brand.brand_list, name='brand_list'),
    path('classification/brand/brands/', brand.get_brand_options, name='brand_options'),

    # 🆕 브랜드 관리 URL 패턴
    path('classification/brand/create/', brand.brand_create, name='brand_create'),
    path('classification/brand/<int:brand_id>/detail/', brand.brand_detail, name='brand_detail'),
    path('classification/brand/<int:brand_id>/update/', brand.brand_update, name='brand_update'),
    path('classification/brand/<int:brand_id>/delete/', brand.brand_delete, name='brand_delete'),

    # 🔗 브랜드 별칭 관리
    path('classification/brand/alias/create/', brand.alias_create, name='brand_alias_create'),
    path('classification/brand/alias/<int:alias_id>/delete/', brand.alias_delete, name='brand_alias_delete'),
    path('classification/brand/<int:brand_id>/toggle/', brand.brand_toggle_active, name='brand_toggle_active'),

]