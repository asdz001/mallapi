import os
from django.contrib import messages
from pathlib import Path

# ✅ 실제 실패 로그 폴더 경로
EVENT_LOG_PATH = Path("eventlog/logs")  # ❗ 로그가 저장되는 실제 경로 확인해서 맞춰야 함

def clear_event_logs(modeladmin, request, queryset):
    """
    Admin 액션: eventlog/logs 내 로그 파일 전체 삭제
    """
    deleted_count = 0

    if not EVENT_LOG_PATH.exists():
        messages.warning(request, f"⚠️ 로그 경로가 존재하지 않습니다: {EVENT_LOG_PATH}")
        return

    try:
        for fname in os.listdir(EVENT_LOG_PATH):
            file_path = EVENT_LOG_PATH / fname
            if file_path.is_file():
                file_path.unlink()
                deleted_count += 1

        messages.success(request, f"✅ 실패 로그 삭제 완료: {deleted_count}개 파일 삭제됨")
    except Exception as e:
        messages.error(request, f"❌ 삭제 중 오류 발생: {str(e)}")
