import os
import psutil
import shutil
import time

def get_enhanced_server_status():
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu = psutil.cpu_percent(interval=1)
    disk = shutil.disk_usage("/")

    mem_percent = round(mem.used / mem.total * 100, 1)
    swap_percent = round(swap.used / swap.total * 100, 1) if swap.total else 0
    disk_percent = round(disk.used / disk.total * 100, 1)

    # 네트워크 속도 (1초간 측정)
    net1 = psutil.net_io_counters()
    time.sleep(1)
    net2 = psutil.net_io_counters()
    net_recv = round((net2.bytes_recv - net1.bytes_recv) / 1024 / 1024, 2)
    net_sent = round((net2.bytes_sent - net1.bytes_sent) / 1024 / 1024, 2)

    try:
        load_avg = tuple(round(x, 2) for x in os.getloadavg())
    except (AttributeError, OSError):
        load_avg = ("N/A", "N/A", "N/A")

    warnings = []
    if cpu > 85:
        warnings.append("CPU 사용률이 85% 초과")
    if mem_percent > 85:
        warnings.append("메모리 사용률이 85% 초과")
    if swap_percent > 50:
        warnings.append("스왑 메모리 50% 초과")
    if disk_percent > 90:
        warnings.append("디스크 사용량 90% 초과")

    status_msg = "✅ 정상" if not warnings else "⚠️ 주의: " + " / ".join(warnings)

    return {
        "cpu": cpu,
        "mem_total": round(mem.total / (1024 ** 3), 2),
        "mem_used": round(mem.used / (1024 ** 3), 2),
        "mem_percent": mem_percent,
        "swap_used": round(swap.used / (1024 ** 3), 2),
        "swap_percent": swap_percent,
        "disk_total": round(disk.total / (1024 ** 3), 2),
        "disk_used": round(disk.used / (1024 ** 3), 2),
        "disk_percent": disk_percent,
        "net_recv": net_recv,
        "net_sent": net_sent,
        "load_avg": load_avg,
        "status_msg": status_msg,
        "cpu_message": "🔥 과부하" if cpu > 85 else ("⚠️ 주의" if cpu > 60 else "✅ 정상"),
        "mem_message": "🔥 과부하" if mem_percent > 85 else ("⚠️ 주의" if mem_percent > 60 else "✅ 정상"),
        "swap_message": "⚠️ 사용 중" if swap_percent > 30 else "✅ 미사용",
        "disk_message": "🔥 디스크 부족" if disk_percent > 90 else ("⚠️ 사용량 높음" if disk_percent > 75 else "✅ 여유 있음"),
    }
