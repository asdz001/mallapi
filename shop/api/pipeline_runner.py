# shop/api/pipeline_runner.py

from django.utils import timezone
from pricing.models import Retailer
from shop.models import RawProduct  # ✅ 이거 꼭 필요!

def run_full_pipeline_by_retailer(retailer_code):
    """
    거래처 코드에 따라 수집 → 등록 실행 + 실행 이력 기록
    관리자/스케줄러 공통 함수입니다.
    """
    retailer = Retailer.objects.get(code=retailer_code)

    # 수집 시작 시간 기록
    retailer.last_fetch_started_at = timezone.now()
    retailer.save()

# 거래처별 분기
    #라띠
    if retailer_code == "IT-R-01":  # LATTI
        from shop.api.latti.latti import fetch_latti_raw_products_optimized
        from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer

        fetch_count = fetch_latti_raw_products_optimized()
        bulk_convert_or_update_products_by_retailer(retailer_code)
        register_count = RawProduct.objects.filter(retailer=retailer_code, status='converted').count()



    #바제블루
    elif retailer_code == "IT-B-01":  # BASEBLU
        from shop.api.baseblu.basebiu import run_full_baseblue_pipeline
        from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer

        fetch_count = run_full_baseblue_pipeline()  # limit 생략 or 넣을 수 있음
        bulk_convert_or_update_products_by_retailer(retailer_code)
        register_count = RawProduct.objects.filter(retailer=retailer_code, status='converted').count()
  
#아뜰리에 API 업체 

    #쿠쿠이니
    elif retailer_code == "IT-C-02":
        from shop.management.commands.fetch_and_register_minetti import Command
        cmd = Command()
        return cmd.handle()
    

    #비니실비아
    elif retailer_code == "IT-B-02":
        from shop.management.commands.fetch_and_register_minetti import Command
        cmd = Command()
        return cmd.handle()
    

    #미네띠
    elif retailer_code == "IT-M-01":
        from shop.management.commands.fetch_and_register_minetti import Command
        cmd = Command()
        return cmd.handle()



    else:
        raise ValueError(f"알 수 없는 거래처 코드: {retailer_code}")

    # 완료 시간 및 수량 기록
    retailer.last_fetch_finished_at = timezone.now()
    retailer.last_register_finished_at = timezone.now()
    retailer.last_fetched_count = fetch_count or 0         # ✅ None 방지
    retailer.last_registered_count = register_count or 0   # ✅ None 방지

    try:
        retailer.save()
    except Exception as e:
        print(f"❌ Retailer 저장 실패: {e}")


    return fetch_count or 0, register_count or 0
