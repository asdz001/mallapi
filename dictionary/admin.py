from django.contrib import admin , messages
from django.urls import path
from .models import Brand, BrandAlias
from .models import CategoryLevel1, CategoryLevel1Alias,CategoryLevel2,CategoryLevel2Alias,CategoryLevel3, CategoryLevel3Alias,CategoryLevel4, CategoryLevel4Alias
from django.shortcuts import render, redirect
import pandas as pd
from io import BytesIO
from django.http import HttpResponse




def alias_list(obj):
    return ", ".join(alias.alias for alias in obj.aliases.all())
alias_list.short_description = "치환 값들"

# ✅ 브랜드매핑
class BrandAliasInline(admin.TabularInline):
    model = BrandAlias
    extra = 1

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', alias_list]
    inlines = [BrandAliasInline]
    search_fields = ['name']
    change_list_template = "admin/brand_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('brand/import-alias/', self.admin_site.admin_view(self.import_alias), name='dictionary_brand_import_alias'),
            path('brand/import-alias/example/', self.admin_site.admin_view(self.download_example), name='dictionary_brand_import_alias_example'),
            path('brand/export-alias/', self.admin_site.admin_view(self.export_all_excel), name='dictionary_brand_export_all'),  # ✅ 추가
        ]
        return my_urls + urls
    
    #전체 다운로드
    def export_all_excel(self, request):
        data = []
        for brand in Brand.objects.all():
            for alias in brand.aliases.all():  # ✅ 수정된 부분
                data.append({
                    "표준브랜드명": brand.name,
                    "치환브랜드명": alias.alias,
                })

        df = pd.DataFrame(data)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        buffer.seek(0)
        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename=\"brand_alias_all.xlsx\"'
        return response



    def import_alias(self, request):
        if request.method == "POST" and request.FILES.get("excel_file"):
            excel_file = request.FILES["excel_file"]
            df = pd.read_excel(excel_file)

            created_count = 0
            skipped_count = 0

            for _, row in df.iterrows():
                std_name = str(row.get("표준브랜드명")).strip()
                alias_name = str(row.get("치환브랜드명")).strip()

                if not std_name or not alias_name:
                    skipped_count += 1
                    continue

                # 표준 브랜드 가져오기 (없는 경우 생성)
                brand, _ = Brand.objects.get_or_create(name=std_name)

                # 중복 여부 체크 (대소문자 구분)
                if not BrandAlias.objects.filter(brand=brand, alias=alias_name).exists():
                    BrandAlias.objects.create(brand=brand, alias=alias_name)
                    created_count += 1
                else:
                    skipped_count += 1

            self.message_user(request, f"✅ 등록: {created_count}개, ⏭ 중복/누락: {skipped_count}개")
            return redirect("..")

        return render(request, "admin/import_brand_alias.html")   
    def download_example(self, request):
        # 예제 데이터 생성
        data = {
            "표준브랜드명": ["GUCCI", "PRADA"],
            "치환브랜드명": ["구찌", "프라다"],
        }
        df = pd.DataFrame(data)

        # 메모리 내 엑셀 파일 생성
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="brand_alias_example.xlsx"'
        return response     



# ✅ 카테고리매핑

# 공통 인라인
class BaseCategoryAliasInline(admin.TabularInline):
    extra = 1

# 공통 엑셀 업로드 함수
class BaseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'alias_list']
    search_fields = ['name']
    category_slug = ""  # 경로용
    alias_model = None
    example_filename = ""
    change_list_template = "admin/category_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-alias/', self.admin_site.admin_view(self.import_alias), name=f'dictionary_{self.category_slug}_import_alias'),
            path('import-alias/example/', self.admin_site.admin_view(self.download_example), name=f'dictionary_{self.category_slug}_import_alias_example'),
            path('export-alias/', self.admin_site.admin_view(self.export_all_excel), name=f'dictionary_{self.category_slug}_export_all'),  # ✅ 추가
    
        ]
        return my_urls + urls
    
    #전체 파일 다운로드
    def export_all_excel(self, request):
        data = []
        for category in self.model.objects.all():
            for alias in self.alias_model.objects.filter(category=category):
                data.append({
                    "표준카테고리명": category.name,
                    "치환명": alias.alias,
                })

        df = pd.DataFrame(data)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        buffer.seek(0)
        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename=\"{self.category_slug}_alias_all.xlsx\"'
        return response




    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['upload_url'] = f"/admin/dictionary/{self.category_slug}/import-alias/"
        return super().changelist_view(request, extra_context=extra_context)

    def import_alias(self, request):
        if request.method == "POST" and request.FILES.get("excel_file"):
            excel_file = request.FILES["excel_file"]
            df = pd.read_excel(excel_file)

            created_count = 0
            skipped_count = 0

            for _, row in df.iterrows():
                std_name = str(row.get("표준카테고리명")).strip().upper()
                alias_name = str(row.get("치환명")).strip()

                if not std_name or not alias_name:
                    skipped_count += 1
                    continue

                category, _ = self.model.objects.get_or_create(name=std_name)

                # 🔍 치환명이 이미 다른 표준명과 연결되어 있는지 확인
                existing_alias = self.alias_model.objects.filter(alias=alias_name).first()

                if existing_alias:
                    # 이미 등록된 치환명인데, 다른 표준명이라면 중복으로 판단하고 스킵
                    if existing_alias.category != category:
                        skipped_count += 1
                        continue

                # 동일한 표준명-치환명 조합이 없으면 새로 등록
                if not self.alias_model.objects.filter(category=category, alias=alias_name).exists():
                    self.alias_model.objects.create(category=category, alias=alias_name)
                    created_count += 1
                else:
                    skipped_count += 1

            self.message_user(request, f"✅ 등록: {created_count}개, ⏭ 중복/누락: {skipped_count}개")
            return redirect("..")

        return render(request, "admin/import_category_alias.html", {
            "category_name": self.category_slug.upper(),
            "example_url": f"/admin/dictionary/{self.category_slug}/import-alias/example/",
            "upload_url": f"/admin/dictionary/{self.category_slug}/import-alias/",
        })

    def download_example(self, request):
        data = {
            "표준카테고리명": ["의류", "가방"],
            "치환명": ["CLOTHES", "BAG"],
        }
        df = pd.DataFrame(data)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{self.example_filename}"'
        return response

# ✅ 성별
class CategoryLevel1AliasInline(BaseCategoryAliasInline):
    model = CategoryLevel1Alias

@admin.register(CategoryLevel1)
class CategoryLevel1Admin(BaseCategoryAdmin):
    inlines = [CategoryLevel1AliasInline]
    category_slug = "categorylevel1"
    alias_model = CategoryLevel1Alias
    example_filename = "category1_alias_example.xlsx"

    def alias_list(self, obj):
        return ", ".join(alias.alias for alias in obj.aliases.all())
    alias_list.short_description = "치환 성별"

# ✅ 대분류
class CategoryLevel2AliasInline(BaseCategoryAliasInline):
    model = CategoryLevel2Alias

@admin.register(CategoryLevel2)
class CategoryLevel2Admin(BaseCategoryAdmin):
    inlines = [CategoryLevel2AliasInline]
    category_slug = "categorylevel2"
    alias_model = CategoryLevel2Alias
    example_filename = "category2_alias_example.xlsx"

    def alias_list(self, obj):
        return ", ".join(alias.alias for alias in obj.aliases.all())
    alias_list.short_description = "치환 대분류"

# ✅ 중분류
class CategoryLevel3AliasInline(BaseCategoryAliasInline):
    model = CategoryLevel3Alias

@admin.register(CategoryLevel3)
class CategoryLevel3Admin(BaseCategoryAdmin):
    inlines = [CategoryLevel3AliasInline]
    category_slug = "categorylevel3"
    alias_model = CategoryLevel3Alias
    example_filename = "category3_alias_example.xlsx"

    def alias_list(self, obj):
        return ", ".join(alias.alias for alias in obj.aliases.all())
    alias_list.short_description = "치환 중분류"

# ✅ 소분류
class CategoryLevel4AliasInline(BaseCategoryAliasInline):
    model = CategoryLevel4Alias

@admin.register(CategoryLevel4)
class CategoryLevel4Admin(BaseCategoryAdmin):
    inlines = [CategoryLevel4AliasInline]
    category_slug = "categorylevel4"
    alias_model = CategoryLevel4Alias
    example_filename = "category4_alias_example.xlsx"

    def alias_list(self, obj):
        return ", ".join(alias.alias for alias in obj.aliases.all())
    alias_list.short_description = "치환 소분류"