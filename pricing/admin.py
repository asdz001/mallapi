# pricing/admin.py - 기존 코드에 최적화된 비동기 처리 적용

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
from pricing.models import RetailerSeasonSummary
from collections import defaultdict
from django.template.response import TemplateResponse
from shop.utils.markup_util import get_markup_from_product
from shop.services.price_calculator import calculate_final_price

# ✅ 비동기 처리를 위한 import 추가
import threading
from django.core.cache import cache
from pricing.utils.price_update_utils import update_all_products_pricing, update_products_by_retailer
from utils.bulk_update_logger import get_bulk_update_logger, log_progress


# ✅ 최적화된 비동기 처리 유틸리티
def run_async_price_update(request, update_func, success_message, cache_key='bulk_update_running'):
    """
    통합된 비동기 가격 업데이트 실행기
    
    Args:
        request: Django request 객체
        update_func: 실행할 업데이트 함수 (람다 또는 함수)
        success_message: 성공 시 표시할 메시지
        cache_key: 중복 실행 방지용 캐시 키
    
    Returns:
        bool: 실행 성공 여부
    """
    # 중복 실행 체크
    if cache.get(cache_key):
        request._messages.add(
            messages.WARNING,
            "⚠️ 이미 가격 업데이트 작업이 진행 중입니다. 완료 후 다시 시도해주세요."
        )
        return False
    
    # 백그라운드 함수 정의
    def background_task():
        logger = get_bulk_update_logger()
        try:
            log_progress(logger, f"[비동기] 가격 업데이트 시작 - 사용자: {request.user.username}")
            
            # 실제 업데이트 실행
            result = update_func()
            
            log_progress(logger, f"[비동기] 가격 업데이트 완료 - 결과: {result}")
            
        except Exception as e:
            log_progress(logger, f"[비동기] 가격 업데이트 실패 - 오류: {str(e)}")
            logger.error(f"[비동기 작업 에러] {str(e)}", exc_info=True)
        finally:
            cache.delete(cache_key)
            log_progress(logger, "[비동기] 작업 종료, 캐시 플래그 해제")
    
    # 캐시 설정 및 스레드 시작
    cache.set(cache_key, True, timeout=3600)  # 1시간 안전장치
    thread = threading.Thread(target=background_task, daemon=True)
    thread.start()
    
    # 즉시 메시지 표시
    request._messages.add(messages.SUCCESS, success_message)
    return True


# ✅ BrandMarkupDetail Inline Admin (기존 코드 유지)
class BrandMarkupDetailInline(admin.TabularInline):
    model = BrandMarkupDetail
    extra = 1
    min_num = 0
    fields = ('gender', 'category', 'markup', 'is_active')
    verbose_name = "세부 마크업"
    verbose_name_plural = "성별/카테고리별 마크업 설정"


# ✅ BrandSetting Admin (기존 코드 유지)
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
        """Inline 저장 시 생성자/수정자 기록 및 비동기 가격 업데이트"""
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            instance.save()
        formset.save_m2m()
        
        # ✅ 비동기 가격 업데이트 (최적화된 버전)
        if hasattr(form, 'instance') and form.instance:
            retailer_code = form.instance.retailer.code
            
            run_async_price_update(
                request,
                lambda: update_products_by_retailer(retailer_code, request.user),
                f"✅ 마크업 설정이 저장되었습니다. 🚀 {retailer_code} 거래처 상품 가격 업데이트가 백그라운드에서 시작되었습니다."
            )
    
    # ✅ 커스텀 표시 메서드들 (기존 코드 유지)
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
        """엑셀 샘플 파일 다운로드 (기존 코드 유지)"""
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
        """전체 데이터 엑셀 다운로드 (기존 코드 유지)"""
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
        """엑셀 파일 대량 업로드 - 기존 로직 + 비동기 업데이트"""
        if request.method == "POST" and request.FILES.get("excel_file"):
            logger = logging.getLogger('brandsetting_import')
            import_start_time = timezone.now()
            upload_filename = request.FILES["excel_file"].name
            
            logger.info(f"[브랜드설정 엑셀 업로드 시작] 파일명: {upload_filename} | 사용자: {request.user.username}")
            
            try:
                df = pd.read_excel(request.FILES["excel_file"])
                created_settings, updated_settings, skipped = 0, 0, 0
                failed_rows = []
                
                # ✅ 기존 데이터 처리 로직 (동일)
                grouped_data = {}
                affected_retailers = set()
                
                for idx, row in df.iterrows():
                    try:
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
                            logger.error(f"[행 {idx + 2}] {error_msg} | 데이터: {dict(row)}")
                            skipped += 1
                            continue
                        
                        try:
                            retailer = Retailer.objects.get(code=retailer_code)
                            affected_retailers.add(retailer_code)
                        except Retailer.DoesNotExist:
                            error_msg = f"거래처 찾을 수 없음: {retailer_code}"
                            failed_rows.append({
                                "행번호": idx + 2,
                                "오류": error_msg,
                                "데이터": dict(row)
                            })
                            logger.error(f"[행 {idx + 2}] {error_msg} | 데이터: {dict(row)}")
                            skipped += 1
                            continue
                        
                        setting_key = (retailer_code, brand_name, seasons, int(priority))
                        
                        if setting_key not in grouped_data:
                            grouped_data[setting_key] = {
                                'retailer': retailer,
                                'brand_name': brand_name,
                                'seasons': seasons,
                                'priority': int(priority),
                                'markups': [],
                                'excel_combinations': set(),
                                'row_numbers': []
                            }
                        
                        markup_combination = (gender, category)
                        
                        if markup_combination in grouped_data[setting_key]['excel_combinations']:
                            error_msg = f"중복된 성별+카테고리 조합: {gender}-{category}"
                            failed_rows.append({
                                "행번호": idx + 2,
                                "오류": error_msg,
                                "데이터": dict(row)
                            })
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
                        logger.error(f"[행 {idx + 2}] {error_msg} | 데이터: {dict(row)} | 상세오류: {traceback.format_exc()}")
                        skipped += 1
                        continue
                
                # ✅ 기존 DB 저장 로직 (동일)
                for setting_key, data in grouped_data.items():
                    try:
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
                        
                        deleted_count = 0
                        for gender, category, markup in data['markups']:
                            deleted, _ = BrandMarkupDetail.objects.filter(
                                brand_setting=brand_setting,
                                gender=gender,
                                category=category
                            ).delete()
                            deleted_count += deleted
                        
                        logger.info(f"   🗑️ 기존 마크업 삭제: {deleted_count}개")
                        
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
                        logger.error(f"[행 {data['row_numbers']}] {error_msg} | 브랜드: {data['brand_name']} | 상세오류: {traceback.format_exc()}")
                        skipped += 1
                        continue
                
                # ✅ 비동기 가격 업데이트 (최적화된 버전)
                success_msg = f"✅ 브랜드설정 생성: {created_settings}개, ✏️ 수정: {updated_settings}개, ⏭️ 건너뜀: {skipped}개"
                
                if affected_retailers:
                    # 각 거래처별로 비동기 업데이트
                    for retailer_code in affected_retailers:
                        run_async_price_update(
                            request,
                            lambda rc=retailer_code: update_products_by_retailer(rc, request.user),
                            f"{success_msg} | 🚀 {len(affected_retailers)}개 거래처 상품 가격 업데이트가 백그라운드에서 시작되었습니다.",
                            cache_key=f'bulk_update_running_{retailer_code}'
                        )
                
                # ✅ 최종 결과 로그 기록 (기존과 동일)
                total_processed = len(df)
                processing_time = (timezone.now() - import_start_time).total_seconds()
                
                logger.info(f"[브랜드설정 엑셀 업로드 완료] 총 처리: {total_processed}행 | 생성: {created_settings}개 | 수정: {updated_settings}개 | 실패: {skipped}개 | 처리시간: {processing_time:.2f}초")
                
                if failed_rows:
                    logger.warning(f"[실패 요약] 총 {len(failed_rows)}개 행 실패")
                    
                    print("\n" + "="*50)
                    print("❌ 실패한 행들:")
                    print("="*50)
                    for fail in failed_rows:
                        print(f"행 {fail['행번호']}: {fail['오류']}")
                        if 'data' in fail:
                            print(f"   데이터: {fail['data']}")
                        print("-"*30)
                    
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
                logger.error(f"[치명적 오류] {error_msg} | 상세오류: {traceback.format_exc()}")
                
                self.message_user(
                    request, 
                    f"❌ {error_msg}", 
                    level=messages.ERROR
                )
        
        return render(request, "admin/import_brandsettings.html")


# ✅ BrandMarkupDetail 독립 Admin (비동기 처리 적용)
@admin.register(BrandMarkupDetail)
class BrandMarkupDetailAdmin(admin.ModelAdmin):
    list_display = ['brand_setting', 'gender', 'category', 'markup', 'is_active', 'created_at']
    list_filter = ['gender', 'category', 'is_active', 'brand_setting__retailer']
    search_fields = ['brand_setting__brand_name', 'brand_setting__retailer__name']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('brand_setting', 'brand_setting__retailer')

    def save_model(self, request, obj, form, change):
        """저장 후 비동기 상품 마크업 업데이트"""
        super().save_model(request, obj, form, change)
        
        retailer_code = obj.brand_setting.retailer.code
        run_async_price_update(
            request,
            lambda: update_products_by_retailer(retailer_code, request.user),
            f"✅ 마크업이 저장되었습니다. 🚀 {retailer_code} 거래처 상품 가격 업데이트가 백그라운드에서 시작되었습니다."
        )


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


# ✅ FTA 관련 관리자들 (비동기 처리 적용)
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

    def save_model(self, request, obj, form, change):
        """FTA 설정 변경 시 비동기 상품 가격 업데이트"""
        super().save_model(request, obj, form, change)

        run_async_price_update(
            request,
            lambda: update_all_products_pricing(request.user, f"FTA설정변경({obj.name})"),
            f"✅ {obj.name}의 FTA 설정이 저장되었습니다. 🚀 전체 상품 가격 업데이트가 백그라운드에서 시작되었습니다."
        )
    
    def save_formset(self, request, form, formset, change):
        """CountryAlias 인라인 저장 시 비동기 처리"""
        super().save_formset(request, form, formset, change)
        
        run_async_price_update(
            request,
            lambda: update_all_products_pricing(request.user, "국가별칭변경"),
            "✅ 국가별칭이 저장되었습니다. 🚀 전체 상품 가격 업데이트가 백그라운드에서 시작되었습니다."
        )

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
        """엑셀 업로드 후 비동기 가격 업데이트"""
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

            # ✅ 비동기 가격 업데이트
            run_async_price_update(
                request,
                lambda: update_all_products_pricing(request.user, "FTA엑셀업로드"),
                f"✅ FTA 설정 등록됨: {created}개, ⏭ 건너뜀: {skipped}개 | 🚀 전체 상품 가격 업데이트가 백그라운드에서 시작되었습니다."
            )
            return redirect("..")

        return render(request, "admin/import_fixedcountry.html", {
            "upload_url": reverse("admin:dictionary_fixedcountry_import_excel"),
            "example_url": reverse("admin:dictionary_fixedcountry_import_example"),
        })

    def download_example(self, request):
        """엑셀 샘플 파일 다운로드"""
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
        """전체 데이터 엑셀 다운로드"""
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
        """원본 국가명 목록 표시"""
        aliases = obj.countryalias_set.all().values_list('origin_name', flat=True)
        return ", ".join(aliases) if aliases else "-"
    alias_list.short_description = "원본 국가명"


# ✅ 표준계산식 관리자 (비동기 처리 적용)
class PriceFormulaRangeInline(admin.TabularInline):
    model = PriceFormulaRange
    extra = 1

@admin.register(GlobalPricingSetting)
class GlobalPricingSettingAdmin(admin.ModelAdmin):
    list_display = (
        'exchange_rate', 'shipping_fee', 'VAT', 'margin_rate', 'special_tax_rate'
    )
    inlines = [PriceFormulaRangeInline]
    
    def save_model(self, request, obj, form, change):
        """환율/배송비/마진율 변경 시 비동기 상품 가격 업데이트"""
        super().save_model(request, obj, form, change)
        
        run_async_price_update(
            request,
            lambda: update_all_products_pricing(request.user, "전체상품업데이트(비동기)"),
            "✅ 설정이 저장되었습니다. 🚀 전체 상품 가격 업데이트가 백그라운드에서 시작되었습니다. (완료까지 약 5분 소요)"
        )
    
    def save_formset(self, request, form, formset, change):
        """PriceFormulaRange 인라인 저장 시 비동기 처리"""
        super().save_formset(request, form, formset, change)
        
        run_async_price_update(
            request,
            lambda: update_all_products_pricing(request.user, "전체상품업데이트(가격구간변경)"),
            "✅ 가격 구간 설정이 저장되었습니다. 🚀 전체 상품 가격 업데이트가 백그라운드에서 시작되었습니다."
        )


# ✅ 거래처 시즌 요약 관리자 (기존 코드 유지)
@admin.register(RetailerSeasonSummary)
class RetailerSeasonSummaryAdmin(admin.ModelAdmin):
    change_list_template = "admin/retailer_season_summary.html"
    model = RetailerSeasonSummary  # 실제 모델은 아님

    def changelist_view(self, request, extra_context=None):
        season_map = defaultdict(set)

        # Product에서 리테일러-시즌 수집
        for row in Product.objects.exclude(season__isnull=True).exclude(season="").values("retailer", "season").distinct():
            season_map[row["retailer"]].add(row["season"].strip())

        summary = [
            {"retailer": k, "seasons": ", ".join(sorted(v))}
            for k, v in sorted(season_map.items())
        ]

        context = {
            "title": "거래처별 시즌 요약 보기",
            "summary_list": summary
        }
        return TemplateResponse(request, "admin/retailer_season_summary.html", context)


# ✅ 작업 상태 확인 유틸리티 함수들
def is_bulk_update_running(cache_key='bulk_update_running'):
    """현재 가격 업데이트 작업이 실행 중인지 확인"""
    return cache.get(cache_key, False)

def get_bulk_update_status():
    """가격 업데이트 작업 상태 반환"""
    return {
        'is_running': cache.get('bulk_update_running', False),
        'cache_key': 'bulk_update_running'
    }