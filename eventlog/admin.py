from django.conf import settings
from django.urls import path
from django.shortcuts import redirect
from django.contrib import admin, messages
from eventlog.models import ConversionLog
from django.http import HttpResponse
import csv
import subprocess, os, sys
from pathlib import Path


@admin.register(ConversionLog)
class ConversionLogAdmin(admin.ModelAdmin):
    list_display = ["retailer", "id", "source", "raw_product", "reason", "created_at"]
    search_fields = ["retailer", "reason", "raw_product__product_name"]
    list_filter = ["retailer", "source", "created_at"]
    readonly_fields = ["raw_product", "reason", "created_at", "source"]
    change_list_template = "admin/conversionlog/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("export-all/", self.admin_site.admin_view(self.export_all_logs), name="conversionlog_export_all"),
            path("export-and-clear/", self.admin_site.admin_view(self.export_and_clear_logs), name="conversionlog_export_and_clear"),
        ]
        return custom_urls + urls

    def export_all_logs(self, request):
        logs = ConversionLog.objects.all().select_related("raw_product")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="conversion_failures_all.csv"'
        response.write(u'\ufeff'.encode('utf8'))  # ✅ UTF-8 BOM for Excel compatibility

        writer = csv.writer(response)
        writer.writerow([
            "상품 ID", "브랜드", "성별", "카테고리1", "카테고리2", "원산지",
            "브랜드 실패", "카테고리 실패", "원산지 실패", "실패사유"
        ])

        for log in logs:
            rp = log.raw_product
            brand_fail = rp.raw_brand_name if "브랜드 실패" in log.reason else "성공"
            category_fail = f"{rp.category1}/{rp.gender}/{rp.category2}" if "카테고리 실패" in log.reason else "성공"
            origin_fail = rp.origin if "원산지 실패" in log.reason else "성공"

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
                log.reason
            ])

        return response

    def export_and_clear_logs(self, request):
        """log_export_and_clear 명령어 실행 (관리자 버튼용)"""
        try:
            python_path = sys.executable
            manage_py = Path(settings.BASE_DIR) / "manage.py"  # 경로 정확히

            # ✅ 경로 확인용 출력 (테스트용, 삭제 가능)
            print("PYTHON:", python_path)
            print("MANAGE:", manage_py)

            subprocess.run(
                [python_path, str(manage_py), "log_export_and_clear"],
                check=True
            )
            self.message_user(request, "✅ 2일 이상 된 로그 백업 및 삭제 완료!", messages.SUCCESS)
        except subprocess.CalledProcessError as e:
            self.message_user(request, f"❌ 실행 중 오류 발생: {e}", messages.ERROR)
        except Exception as e:
            self.message_user(request, f"❌ 예상치 못한 오류 발생: {e}", messages.ERROR)

        return redirect("..")
