from django.urls import path
from django.shortcuts import redirect
from django.contrib import admin, messages
from eventlog.models import ConversionLog
from django.http import HttpResponse
import csv


@admin.register(ConversionLog)
class ConversionLogAdmin(admin.ModelAdmin):
    list_display = [ "retailer", "id", "source", "raw_product", "reason", "created_at"]
    search_fields = [ "retailer", "reason", "raw_product__product_name"]
    list_filter = [ "retailer", "source", "created_at"]
    readonly_fields = ["raw_product", "reason", "created_at", "source"]
    change_list_template = "admin/conversionlog/change_list.html"  # 👈 템플릿 오버라이드



    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("export-all/", self.admin_site.admin_view(self.export_all_logs), name="conversionlog_export_all"),
        ]
        return custom_urls + urls

    def export_all_logs(self, request):
        logs = ConversionLog.objects.all().select_related("raw_product")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="conversion_failures_all.csv"'
        response.write(u'\ufeff'.encode('utf8'))  # UTF-8 BOM

        writer = csv.writer(response)
        writer.writerow([
            "상품 ID", "브랜드", "성별", "카테고리1", "카테고리2", "원산지",
            "브랜드 실패", "카테고리 실패", "원산지 실패", "실패사유"
        ])

        for log in logs:
            rp = log.raw_product
            brand_fail = category_fail = origin_fail = ""

            if "브랜드 실패" in log.reason:
                brand_fail = rp.raw_brand_name
            else:
                brand_fail = "성공"

            if "카테고리 실패" in log.reason:
                category_fail = f"{rp.category1}/{rp.gender}/{rp.category2}"
            else:
                category_fail = "성공"

            if "원산지 실패" in log.reason:
                origin_fail = rp.origin
            else:
                origin_fail = "성공"

            writer.writerow([
                rp.external_product_id,
                rp.raw_brand_name,
                rp.gender,
                rp.category1,
                rp.category2,
                rp.origin,
                brand_fail,
                category_fail,
                origin_fail,
                log.reason  # ✅ 전체 실패사유 요약 컬럼
            ])

        return response