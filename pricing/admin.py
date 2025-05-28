from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect
import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from .models import BrandSetting
from .models import Retailer
from .models import FixedCountry, CountryAlias
from .models import GlobalPricingSetting
from .models import PriceFormulaRange



#브랜드
@admin.register(BrandSetting)
class BrandSettingAdmin(admin.ModelAdmin):
    list_display = ["retailer", "season" , "brand_name", "get_categories", "markup"]
    list_filter = ["retailer", "season","markup"]
    search_fields = ["brand_name", "season"]
    change_list_template = "admin/brandsetting_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-excel/", self.admin_site.admin_view(self.import_excel), name="pricing_brandsetting_import_excel"),
            path("import-excel/example/", self.admin_site.admin_view(self.download_example), name="pricing_brandsetting_import_example"),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context["upload_url"] = "/admin/pricing/brandsetting/import-excel/"
        return super().changelist_view(request, extra_context=extra_context)

    def import_excel(self, request):
        if request.method == "POST" and request.FILES.get("excel_file"):
            df = pd.read_excel(request.FILES["excel_file"])

            created, updated, skipped = 0, 0, 0

            for _, row in df.iterrows():
                retailer_code = str(row.get("업체코드", "")).strip()
                season = str(row.get("시즌", "")).strip()
                brand_name = str(row.get("브랜드명", "")).strip()
                category = str(row.get("카테고리", "")).strip()
                markup = row.get("마크업율", None)
                

                print(f"▶️ 행 입력값: {retailer_code}, {brand_name}, {category}, {markup}, {season}")

                if not retailer_code or not brand_name or not category or pd.isna(markup):
                    print("⛔ 누락된 값 발견 → 건너뜀")
                    skipped += 1
                    continue

                try:
                    retailer = Retailer.objects.get(code=retailer_code)
                    print(f"✅ retailer 찾음: {retailer}")
                except Retailer.DoesNotExist:
                    print(f"❌ retailer 찾을 수 없음: {retailer_code}")
                    skipped += 1
                    continue

                qs = BrandSetting.objects.filter(
                    retailer=retailer,
                    brand_name=brand_name,
                )

                found = False
                for obj in qs:
                    print(f"👁 기존 카테고리: {obj.category1}")
                    if category in (obj.category1 or []):
                        print(f"✏️ 업데이트: {brand_name}/{category} → 마크업 {obj.markup} → {markup}")
                        obj.markup = markup
                        obj.season = season
                        obj.save()
                        updated += 1
                        found = True
                        break

                if not found:
                    print(f"➕ 신규 생성: {brand_name}/{category} with {markup}, {season}")
                    BrandSetting.objects.create(
                        retailer=retailer,
                        brand_name=brand_name,
                        category1=[category],
                        season=season,
                        markup=markup,
                    )
                    created += 1

            print(f"=== 결과 요약: 생성 {created}, 수정 {updated}, 건너뜀 {skipped} ===")
            self.message_user(request, f"✅ 생성: {created}개, ✏ 수정: {updated}개, ⏭ 건너뜀: {skipped}개")
            return redirect("..")

        return render(request, "admin/import_brandsettings.html")

    def download_example(self, request):
        df = pd.DataFrame({
            "업체코드": ["IT-R-01", "IT-G-03"],
            "시즌": ["SS24", "FW23"],
            "브랜드명": ["GUCCI", "PRADA"],
            "카테고리": ["의류", "가방"],
            "마크업율": [2.0, 2.3],
            
        })
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="brandsetting_example.xlsx"'
        return response

    def get_categories(self, obj):
        return ", ".join(obj.category1 or [])
    get_categories.short_description = "카테고리"




#거래처명
@admin.register(Retailer)
class RetailerAdmin(admin.ModelAdmin):
    list_display = ('name', 'code',"order_api_name", )
    search_fields = ('name',)




#FTA적용여부


# ✅ 치환 원산지 CountryAlias를 Inline 형태로 보여줌
class CountryAliasInline(admin.TabularInline):
    model = CountryAlias
    extra = 1  # 빈 입력란 개수
    min_num = 0
    verbose_name = "원본 국가명"
    verbose_name_plural = "원본 국가명 목록"
    show_change_link = True

@admin.register(FixedCountry)
class FixedCountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'alias_list', 'fta_applicable']  # ← alias_list 추가!
    list_filter = ['fta_applicable']
    search_fields = ['name']
    ordering = ['name']
    inlines = [CountryAliasInline]
    change_list_template = "admin/fixedcountry_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-excel/', self.admin_site.admin_view(self.import_excel), name='dictionary_fixedcountry_import_excel'),
            path('import-excel/example/', self.admin_site.admin_view(self.download_example), name='dictionary_fixedcountry_import_example'),
        ]
        return my_urls + urls

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context["upload_url"] = reverse("admin:dictionary_fixedcountry_import_excel")
        return super().changelist_view(request, extra_context=extra_context)

    def import_excel(self, request):
        context = {}
        if request.method == "POST" and request.FILES.get("excel_file"):
            df = pd.read_excel(request.FILES["excel_file"])

            created, skipped = 0, 0
            for _, row in df.iterrows():
                std_name = str(row.get("표준국가명", "")).strip()
                fta_flag = str(row.get("FTA적용", "")).strip().upper() in ["TRUE", "1", "예", "Y"]
                alias_name = str(row.get("치환국가명", "")).strip()

                if not std_name or not alias_name:
                    skipped += 1
                    continue

                country, created_flag = FixedCountry.objects.get_or_create(name=std_name)

                if created_flag:
                    country.fta_applicable = fta_flag
                    country.save()

                if not CountryAlias.objects.filter(standard_country=country, origin_name=alias_name).exists():
                    CountryAlias.objects.create(standard_country=country, origin_name=alias_name)
                    created += 1
                else:
                    skipped += 1

            self.message_user(request, f"✅ 등록됨: {created}개, ⏭ 건너뜀: {skipped}개")
            return redirect("..")

        return render(request, "admin/import_fixedcountry.html", {
            "upload_url": reverse("admin:dictionary_fixedcountry_import_excel"),
            "example_url": reverse("admin:dictionary_fixedcountry_import_example"),
        })

    def download_example(self, request):
        df = pd.DataFrame({
            "표준국가명": ["이탈리아", "미국"],
            "FTA적용": ["TRUE", "FALSE"],
            "치환국가명": ["이태리", "USA"],
        })
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="fixedcountry_example.xlsx"'
        return response

    def alias_list(self, obj):
        aliases = obj.countryalias_set.all().values_list('origin_name', flat=True)
        return ", ".join(aliases) if aliases else "-"
    alias_list.short_description = "원본 국가명"


#표준계산식

class PriceFormulaRangeInline(admin.TabularInline):
    model = PriceFormulaRange
    extra = 1


@admin.register(GlobalPricingSetting)
class GlobalPricingSettingAdmin(admin.ModelAdmin):
    list_display = (
        'exchange_rate', 'shipping_fee', 'VAT', 'margin_rate', 'special_tax_rate'
    )
    inlines = [PriceFormulaRangeInline]