# pricing/admin.py에서 BrandSetting 관련 부분만 새로 작성

from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import render, redirect
import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from .models import BrandSetting, BrandMarkupDetail
from .models import Retailer
from .models import FixedCountry, CountryAlias
from .models import GlobalPricingSetting
from .models import PriceFormulaRange
from django.utils.html import format_html
from django.utils import timezone
from shop.api.pipeline_runner import run_full_pipeline_by_retailer
import traceback
import logging
from shop.models import Product
from django.utils.translation import gettext_lazy as _


# ✅ BrandMarkupDetail Inline Admin
class BrandMarkupDetailInline(admin.TabularInline):
    model = BrandMarkupDetail
    extra = 1
    min_num = 0
    fields = ('gender', 'category', 'markup', 'is_active')
    verbose_name = "세부 마크업"
    verbose_name_plural = "성별/카테고리별 마크업 설정"


# ✅ 새로운 구조에 맞는 BrandSetting Admin
@admin.register(BrandSetting)
class BrandSettingAdmin(admin.ModelAdmin):
    list_display = [
        'retailer', 'brand_name', 'season_display', 'priority_display', 
        'markup_count', 'markup_summary', 'is_active'
    ]
    
    list_filter = ['retailer', 'priority', 'is_active', 'created_at']
    search_fields = ['brand_name', 'seasons']
    
    inlines = [BrandMarkupDetailInline]
    
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = [
        ('기본 정보', {
            'fields': ['retailer', 'brand_name', 'seasons', 'priority']
        }),
        ('설정', {
            'fields': ['is_active', 'description']
        }),
        ('추적 정보', {
            'fields': ['created_at', 'updated_at', 'created_by', 'updated_by'],
            'classes': ['collapse']
        })
    ]
    
    # ✅ 엑셀 업로드/다운로드 URL 추가
    change_list_template = "admin/brandsetting_change_list.html"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-excel/", self.admin_site.admin_view(self.import_excel), 
                 name="pricing_brandsetting_import_excel"),
            path("import-excel/example/", self.admin_site.admin_view(self.download_example), 
                 name="pricing_brandsetting_import_example"),
            path('export-excel/', self.admin_site.admin_view(self.export_all_excel), 
                 name='pricing_brandsetting_export_all'),
        ]
        return custom_urls + urls
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        """Inline 저장 시 생성자/수정자 기록"""
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            instance.save()
        formset.save_m2m()
    
    # ✅ 커스텀 표시 메서드들
    def season_display(self, obj):
        return obj.season_display()
    season_display.short_description = "시즌"
    
    def priority_display(self, obj):
        priority_labels = {1: "1순위", 2: "2순위", 3: "3순위"}
        return priority_labels.get(obj.priority, f"{obj.priority}순위")
    priority_display.short_description = "우선순위"
    
    def markup_count(self, obj):
        count = obj.markup_count()
        if count == 0:
            return format_html('<span style="color: red;">0개</span>')
        return format_html('<span style="color: green;"><strong>{}개</strong></span>', count)
    markup_count.short_description = "마크업 수"
    
    def markup_summary(self, obj):
        summary = obj.markup_summary()
        if "마크업 없음" in summary:
            return format_html('<span style="color: red;">{}</span>', summary)
        return format_html('<span style="color: blue;">{}</span>', summary)
    markup_summary.short_description = "마크업 요약"
    
    # ✅ 엑셀 관련 메서드들
    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context.update({
            "upload_url": reverse("admin:pricing_brandsetting_import_excel"),
            "example_url": reverse("admin:pricing_brandsetting_import_example"),
            "export_url": reverse("admin:pricing_brandsetting_export_all"),
        })
        return super().changelist_view(request, extra_context=extra_context)
    
    def download_example(self, request):
        """엑셀 샘플 파일 다운로드"""
        df = pd.DataFrame({
            "거래처코드": ["IT-R-01", "IT-R-01", "IT-R-01", "IT-R-01", "IT-R-01"],
            "브랜드명": ["GUCCI", "GUCCI", "GUCCI", "PRADA", "ETC"],
            "시즌": ["FW25,SS25", "FW25,SS25", "FW25,SS25", "FW25", "-"],
            "우선순위": [1, 1, 1, 1, 3],
            "성별": ["남성", "남성", "여성", "여성", "전체"],
            "카테고리": ["의류", "가방", "의류", "가방", "전체"],
            "마크업": [2.5, 2.8, 2.3, 2.6, 1.8],
        })
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='브랜드마크업')
        buffer.seek(0)
        
        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="brandsetting_example.xlsx"'
        return response
    
    def export_all_excel(self, request):
        """전체 데이터 엑셀 다운로드"""
        data = []
        
        for brand_setting in BrandSetting.objects.all().prefetch_related('markups'):
            for markup in brand_setting.markups.all():
                data.append({
                    "거래처코드": brand_setting.retailer.code,
                    "거래처명": brand_setting.retailer.name,
                    "브랜드명": brand_setting.brand_name,
                    "시즌": brand_setting.seasons or "",
                    "우선순위": brand_setting.priority,
                    "성별": markup.gender,
                    "카테고리": markup.category,
                    "마크업": markup.markup,
                    "활성화": "TRUE" if brand_setting.is_active else "FALSE",
                    "설명": brand_setting.description or "",
                    "생성일": brand_setting.created_at.strftime("%Y-%m-%d %H:%M") if brand_setting.created_at else "",
                })
        
        df = pd.DataFrame(data)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='브랜드마크업')
        buffer.seek(0)
        
        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="brandsetting_all.xlsx"'
        return response
    
    def import_excel(self, request):
        """엑셀 파일 대량 업로드 - 스마트 업데이트 방식"""
        if request.method == "POST" and request.FILES.get("excel_file"):
            # ✅ 로거 설정
            logger = logging.getLogger('brandsetting_import')
            import_start_time = timezone.now()
            upload_filename = request.FILES["excel_file"].name
            
            logger.info(f"[브랜드설정 엑셀 업로드 시작] 파일명: {upload_filename} | 사용자: {request.user.username}")
            
            try:
                df = pd.read_excel(request.FILES["excel_file"])
                created_settings, updated_settings, skipped = 0, 0, 0
                failed_rows = []
                
                # ✅ 1단계: 데이터를 BrandSetting별로 그룹핑
                grouped_data = {}
                
                for idx, row in df.iterrows():
                    try:
                        # 필수 필드 검증
                        retailer_code = str(row.get("거래처코드", "")).strip()
                        brand_name = str(row.get("브랜드명", "")).strip()
                        seasons = str(row.get("시즌", "")).strip()
                        priority = row.get("우선순위", 1)
                        gender = str(row.get("성별", "")).strip()
                        category = str(row.get("카테고리", "")).strip()
                        markup = row.get("마크업", None)
                        
                        if not all([retailer_code, brand_name, gender, category]) or pd.isna(markup):
                            error_msg = "필수값 누락 (거래처코드, 브랜드명, 성별, 카테고리, 마크업)"
                            failed_rows.append({
                                "행번호": idx + 2,
                                "오류": error_msg,
                                "데이터": dict(row)
                            })
                            # ✅ 로그 파일에 기록
                            logger.error(f"[행 {idx + 2}] {error_msg} | 데이터: {dict(row)}")
                            skipped += 1
                            continue
                        
                        # 거래처 존재 확인
                        try:
                            retailer = Retailer.objects.get(code=retailer_code)
                        except Retailer.DoesNotExist:
                            error_msg = f"거래처 찾을 수 없음: {retailer_code}"
                            failed_rows.append({
                                "행번호": idx + 2,
                                "오류": error_msg,
                                "데이터": dict(row)
                            })
                            # ✅ 로그 파일에 기록
                            logger.error(f"[행 {idx + 2}] {error_msg} | 데이터: {dict(row)}")
                            skipped += 1
                            continue
                        
                        # BrandSetting 그룹핑 키 생성
                        setting_key = (retailer_code, brand_name, seasons, int(priority))
                        
                        if setting_key not in grouped_data:
                            grouped_data[setting_key] = {
                                'retailer': retailer,
                                'brand_name': brand_name,
                                'seasons': seasons,
                                'priority': int(priority),
                                'markups': [],  # [(성별, 카테고리, 마크업), ...]
                                'excel_combinations': set(),  # 엑셀에 포함된 성별+카테고리 조합
                                'row_numbers': []
                            }
                        
                        # 마크업 조합 추가
                        markup_combination = (gender, category)
                        
                        # 중복 체크 (같은 BrandSetting 내에서 성별+카테고리 중복 방지)
                        if markup_combination in grouped_data[setting_key]['excel_combinations']:
                            error_msg = f"중복된 성별+카테고리 조합: {gender}-{category}"
                            failed_rows.append({
                                "행번호": idx + 2,
                                "오류": error_msg,
                                "데이터": dict(row)
                            })
                            # ✅ 로그 파일에 기록
                            logger.error(f"[행 {idx + 2}] {error_msg} | 데이터: {dict(row)}")
                            skipped += 1
                            continue
                        
                        grouped_data[setting_key]['markups'].append((gender, category, float(markup)))
                        grouped_data[setting_key]['excel_combinations'].add(markup_combination)
                        grouped_data[setting_key]['row_numbers'].append(idx + 2)
                        
                    except Exception as e:
                        error_msg = f"데이터 처리 오류: {str(e)}"
                        failed_rows.append({
                            "행번호": idx + 2,
                            "오류": error_msg,
                            "데이터": dict(row)
                        })
                        # ✅ 로그 파일에 기록
                        logger.error(f"[행 {idx + 2}] {error_msg} | 데이터: {dict(row)} | 상세오류: {traceback.format_exc()}")
                        skipped += 1
                        continue
                
                # ✅ 2단계: 그룹핑된 데이터로 DB에 저장
                for setting_key, data in grouped_data.items():
                    try:
                        # BrandSetting 생성/업데이트
                        brand_setting, created_flag = BrandSetting.objects.update_or_create(
                            retailer=data['retailer'],
                            brand_name=data['brand_name'],
                            seasons=data['seasons'],
                            priority=data['priority'],
                            defaults={
                                'is_active': True,
                                'updated_by': request.user,
                            }
                        )
                        
                        if created_flag:
                            brand_setting.created_by = request.user
                            brand_setting.save()
                            created_settings += 1
                            logger.info(f"✅ BrandSetting 생성: {data['brand_name']} | {data['seasons']} | 행: {data['row_numbers']}")
                        else:
                            updated_settings += 1
                            logger.info(f"✏️ BrandSetting 수정: {data['brand_name']} | {data['seasons']} | 행: {data['row_numbers']}")
                        
                        # ✅ 3단계: 엑셀에 포함된 성별+카테고리 조합만 삭제
                        excel_genders = list(set([gender for gender, category, markup in data['markups']]))
                        excel_categories = list(set([category for gender, category, markup in data['markups']]))
                        
                        # 기존 마크업 중 엑셀에 해당하는 조합만 삭제
                        deleted_count = 0
                        for gender, category, markup in data['markups']:
                            deleted, _ = BrandMarkupDetail.objects.filter(
                                brand_setting=brand_setting,
                                gender=gender,
                                category=category
                            ).delete()
                            deleted_count += deleted
                        
                        logger.info(f"   🗑️ 기존 마크업 삭제: {deleted_count}개")
                        
                        # ✅ 4단계: 새로운 마크업들 생성
                        created_markups = []
                        for gender, category, markup in data['markups']:
                            markup_detail = BrandMarkupDetail.objects.create(
                                brand_setting=brand_setting,
                                gender=gender,
                                category=category,
                                markup=markup,
                                is_active=True
                            )
                            created_markups.append(f"{gender}-{category}:{markup}")
                        
                        logger.info(f"   ➕ 새 마크업 생성: {', '.join(created_markups)}")
                            
                    except Exception as e:
                        error_msg = f"DB 저장 오류: {str(e)}"
                        failed_rows.append({
                            "행번호": data['row_numbers'],
                            "오류": error_msg,
                            "브랜드": data['brand_name']
                        })
                        # ✅ 로그 파일에 기록
                        logger.error(f"[행 {data['row_numbers']}] {error_msg} | 브랜드: {data['brand_name']} | 상세오류: {traceback.format_exc()}")
                        skipped += 1
                        continue
                
                # ✅ 5단계: 결과 메시지 및 로그 기록
                success_msg = f"✅ 브랜드설정 생성: {created_settings}개, ✏️ 수정: {updated_settings}개, ⏭️ 건너뜀: {skipped}개"
                
                # ✅ 최종 결과 로그 기록
                total_processed = len(df)
                processing_time = (timezone.now() - import_start_time).total_seconds()
                
                logger.info(f"[브랜드설정 엑셀 업로드 완료] 총 처리: {total_processed}행 | 생성: {created_settings}개 | 수정: {updated_settings}개 | 실패: {skipped}개 | 처리시간: {processing_time:.2f}초")
                
                if failed_rows:
                    # ✅ 실패 요약 로그
                    logger.warning(f"[실패 요약] 총 {len(failed_rows)}개 행 실패")
                    
                    # 콘솔에도 출력 (기존 기능 유지)
                    print("\n" + "="*50)
                    print("❌ 실패한 행들:")
                    print("="*50)
                    for fail in failed_rows:
                        print(f"행 {fail['행번호']}: {fail['오류']}")
                        if 'data' in fail:
                            print(f"   데이터: {fail['data']}")
                        print("-"*30)
                    
                    # 사용자에게도 알림
                    self.message_user(
                        request, 
                        f"{success_msg} | ❌ 실패: {len(failed_rows)}개 (로그 파일 확인)",
                        level=messages.WARNING
                    )
                else:
                    self.message_user(request, success_msg, level=messages.SUCCESS)
                
                return redirect("..")
                
            except Exception as e:
                error_msg = f"파일 처리 중 오류가 발생했습니다: {str(e)}"
                # ✅ 로그 파일에 기록
                logger.error(f"[치명적 오류] {error_msg} | 상세오류: {traceback.format_exc()}")
                
                self.message_user(
                    request, 
                    f"❌ {error_msg}", 
                    level=messages.ERROR
                )
        
        return render(request, "admin/import_brandsettings.html")


# ✅ BrandMarkupDetail 독립 Admin (필요시)
@admin.register(BrandMarkupDetail)
class BrandMarkupDetailAdmin(admin.ModelAdmin):
    list_display = ['brand_setting', 'gender', 'category', 'markup', 'is_active', 'created_at']
    list_filter = ['gender', 'category', 'is_active', 'brand_setting__retailer']
    search_fields = ['brand_setting__brand_name', 'brand_setting__retailer__name']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('brand_setting', 'brand_setting__retailer')


# ✅ 거래처 관리자 (기존 코드 유지)
@admin.register(Retailer)
class RetailerAdmin(admin.ModelAdmin):
    list_display = ('name', 'code',"order_api_name", "auto_schedule", 'current_product_count', "last_fetched_count","last_registered_count",
                    "last_fetch_started_at","last_register_finished_at",'created_by', 'updated_by',"run_auto_pipeline_button")
    search_fields = ('name',)
    readonly_fields = [
        "last_fetch_started_at", "last_fetch_finished_at",
        "last_register_finished_at",
        "last_fetched_count", "last_registered_count",'created_by', 'updated_by',
    ]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def current_product_count(self, obj):
        return Product.objects.filter(retailer=obj.code).count()
    current_product_count.short_description = "가공상품 수"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:retailer_id>/run_pipeline/', self.admin_site.admin_view(self.run_pipeline), name='run_pipeline'),
        ]
        return custom_urls + urls

    def run_auto_pipeline_button(self, obj):
        if obj.is_running:
            return format_html(
                '<a class="button" style="pointer-events:none; background:#ccc;">⏳ 작업 중...</a>'
            )
        return format_html(
            '<a class="button" href="{}">수집 → 등록 실행</a>',
            f"{obj.id}/run_pipeline/"
        )
    run_auto_pipeline_button.short_description = "자동 실행"

    def run_pipeline(self, request, retailer_id):
        logger = logging.getLogger(__name__)
        retailer = Retailer.objects.get(id=retailer_id)
        retailer.last_fetch_started_at = timezone.now()
        retailer.is_running = True
        retailer.save()

        try:
            fetch_count, register_count = run_full_pipeline_by_retailer(retailer.code)
            retailer.refresh_from_db()
            retailer.is_running = False
            retailer.save()
            messages.success(
                request,
                f"{retailer.name} 수집 및 등록 완료: 수집 {fetch_count}개, 등록 {register_count}개"
            )
        except Exception as e:
            logger.error("❌ 파이프라인 실행 중 오류 발생", exc_info=True)
            retailer.is_running = False
            retailer.save()
            messages.error(request, f"❌ 오류 발생: {str(e)}")

        return redirect("..")


# ✅ FTA 관련 관리자들 (기존 코드 유지)
class CountryAliasInline(admin.TabularInline):
    model = CountryAlias
    extra = 1
    min_num = 0
    verbose_name = "원본 국가명"
    verbose_name_plural = "원본 국가명 목록"
    show_change_link = True

@admin.register(FixedCountry)
class FixedCountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'alias_list', 'fta_applicable']
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
            path('export-excel/', self.admin_site.admin_view(self.export_all_excel), name='dictionary_fixedcountry_export_all'),
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
 
    def export_all_excel(self, request):
        data = []
        for country in FixedCountry.objects.all().order_by('name'):
            alias_list = country.countryalias_set.all().values_list("origin_name", flat=True)
            if alias_list:
                for alias in alias_list:
                    data.append({
                        "표준국가명": country.name,
                        "FTA적용": "O" if country.fta_applicable else "X",
                        "치환국가명": alias,
                    })
            else:
                data.append({
                    "표준국가명": country.name,
                    "FTA적용": "O" if country.fta_applicable else "X",
                    "치환국가명": "",
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
        response['Content-Disposition'] = 'attachment; filename="fixedcountry_all.xlsx"'
        return response

    def alias_list(self, obj):
        aliases = obj.countryalias_set.all().values_list('origin_name', flat=True)
        return ", ".join(aliases) if aliases else "-"
    alias_list.short_description = "원본 국가명"


# ✅ 표준계산식 관리자 (기존 코드 유지)
class PriceFormulaRangeInline(admin.TabularInline):
    model = PriceFormulaRange
    extra = 1

@admin.register(GlobalPricingSetting)
class GlobalPricingSettingAdmin(admin.ModelAdmin):
    list_display = (
        'exchange_rate', 'shipping_fee', 'VAT', 'margin_rate', 'special_tax_rate'
    )
    inlines = [PriceFormulaRangeInline]