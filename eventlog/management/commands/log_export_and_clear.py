# eventlog/management/commands/log_export_and_clear.py
from django.core.management.base import BaseCommand
from eventlog.models import ConversionLog
from django.utils.timezone import now, timedelta
import csv
import os

class Command(BaseCommand):
    help = "1일 단위로 실패 로그를 백업하고 삭제합니다."

    def handle(self, *args, **kwargs):
        threshold = now() - timedelta(days=1)
        logs = ConversionLog.objects.filter(created_at__lt=threshold).select_related("raw_product")

        if not logs.exists():
            self.stdout.write("✅ 삭제할 로그 없음")
            return

        filename = f"conversion_log_backup_{now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join("log_backups", filename)
        os.makedirs("log_backups", exist_ok=True)

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["상품 ID", "브랜드", "성별", "카테고리1", "카테고리2", "원산지", "실패 사유"])
            for log in logs:
                rp = log.raw_product
                writer.writerow([
                    rp.external_product_id,
                    rp.raw_brand_name,
                    rp.gender,
                    rp.category1,
                    rp.category2,
                    rp.origin,
                    log.reason
                ])

        deleted, _ = logs.delete()
        self.stdout.write(f"🧹 {deleted}개 로그 백업 후 삭제 완료 → {filename}")
