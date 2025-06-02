# 📄 shop/management/commands/fetch_and_register_all.py

from django.core.management import call_command
from django.core.management.base import BaseCommand
from datetime import datetime

class Command(BaseCommand):
    help = "모든 거래처의 fetch_and_register 작업을 순차적으로 실행합니다."

    def handle(self, *args, **options):
        commands = [
            "fetch_and_register_baseblu",
            "fetch_and_register_bini",
            #"fetch_and_register_cuccuini",
            "fetch_and_register_latti",
            "fetch_and_register_minetti",
        ]

        for cmd in commands:
            start_time = datetime.now()
            self.stdout.write(self.style.NOTICE(f"\n🚀 실행 시작: {cmd} → {start_time.strftime('%Y-%m-%d %H:%M:%S')}"))

            try:
                call_command(cmd)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                self.stdout.write(self.style.SUCCESS(
                    f"✅ 완료: {cmd} → {end_time.strftime('%Y-%m-%d %H:%M:%S')} (소요 시간: {duration:.1f}초)"
                ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ 오류 발생: {cmd} → {e}"))
