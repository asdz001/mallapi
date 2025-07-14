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
    retailer.is_running = True
    retailer.save()


    fetch_count = 0
    register_count = 0    


    try:
        # 거래처별 분기
        # 라띠
        if retailer_code == "IT-R-01":  # LATTI
            from shop.api.latti.latti import fetch_latti_raw_products_optimized
            from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer, sync_soldout_products_from_raw


            fetch_count = fetch_latti_raw_products_optimized()

            bulk_convert_or_update_products_by_retailer(retailer_code)

            sync_soldout_products_from_raw(retailer_code)

            register_count = RawProduct.objects.filter(retailer=retailer_code, status='converted').count()



        # 바제블루
        elif retailer_code == "IT-B-01":  # BASEBLU
            from shop.api.baseblu.basebiu import run_full_baseblue_pipeline
            from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer, sync_soldout_products_from_raw

            fetch_count = run_full_baseblue_pipeline()  # limit 생략 or 넣을 수 있음

            bulk_convert_or_update_products_by_retailer(retailer_code)

            sync_soldout_products_from_raw(retailer_code)
            print(f"🔁 바제블루 품절 반영 완료: {retailer_code}")

            register_count = RawProduct.objects.filter(retailer=retailer_code, status='converted').count()




        # 지앤비
        elif retailer_code == "IT-G-01":
            from shop.api.gnb.gnb import main  # gnb.py의 main 함수만 불러옴
            from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer, sync_soldout_products_from_raw

            # ✅ GNB 상품 수집 및 원본 등록
            fetch_count = main()

            # ✅ 가공상품 등록
            bulk_convert_or_update_products_by_retailer(retailer_code)

            sync_soldout_products_from_raw(retailer_code)

            # ✅ 등록된 상품 수 체크 (가공상품 기준)
            register_count = RawProduct.objects.filter(retailer=retailer_code, status='converted').count()


        # 뉴네스
        elif retailer_code == "IT-N-01":
            from shop.api.nugnes.nugnes import main  # nugnes.py의 main 함수만 불러옴
            from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer, sync_soldout_products_from_raw

            # ✅ GNB 상품 수집 및 원본 등록
            fetch_count = main()

            # ✅ 가공상품 등록
            bulk_convert_or_update_products_by_retailer(retailer_code)

            sync_soldout_products_from_raw(retailer_code)

            # ✅ 등록된 상품 수 체크 (가공상품 기준)
            register_count = RawProduct.objects.filter(retailer=retailer_code, status='converted').count()



        # 리암
        elif retailer_code == "IT-L-01":  # LEAM
            from shop.api.leam.leam import main
            from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer, sync_soldout_products_from_raw

            print("🟡 [1/1] 리암 상품 수집 및 등록 시작")
            fetch_count = main()

            bulk_convert_or_update_products_by_retailer(retailer_code)

            sync_soldout_products_from_raw(retailer_code)

            # ✅ 등록된 상품 수 체크 (가공상품 기준)
            register_count = RawProduct.objects.filter(retailer=retailer_code, status='converted').count()




        # 엘레노라
        elif retailer_code == "IT-E-01":  # 엘레노라
            from shop.api.eleonorabonucci import eleonorabonucci
            from shop.api.eleonorabonucci import register_raw_products
            from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer

            # 1. 수집 및 병합 → JSON
            product_count, _ = eleonorabonucci.fetch_and_merge_all()
            fetch_count = product_count

            # 2. JSON → RawProduct 등록
            register_raw_products.register_raw_products_from_json(test_mode=False)

            # 3. Raw → Product 가공 등록
            bulk_convert_or_update_products_by_retailer(retailer_code)

            # 등록된 개수 측정
            register_count = RawProduct.objects.filter(retailer=retailer_code, status='converted').count()




    #드레스코드

        # 가우덴찌
        elif retailer_code == "IT-G-03":  # GAUDENZI
            from shop.api.dresscode.gaudenzi.gaudenzi import run_gaudenzi_collection
            from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer, sync_soldout_products_from_raw

            fetch_count = run_gaudenzi_collection()

            bulk_convert_or_update_products_by_retailer(retailer_code)

            sync_soldout_products_from_raw(retailer_code)
            print(f"🔁 가우덴찌 품절 반영 완료: {retailer_code}")

            register_count = RawProduct.objects.filter(retailer=retailer_code, status='converted').count()


        # 줄리안
        elif retailer_code == "IT-J-01":  # 
            from shop.api.dresscode.julian.julian import run_julian_collection
            from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer, sync_soldout_products_from_raw

            fetch_count = run_julian_collection()

            bulk_convert_or_update_products_by_retailer(retailer_code)

            sync_soldout_products_from_raw(retailer_code)
            print(f"🔁 줄리안 품절 반영 완료: {retailer_code}")

            register_count = RawProduct.objects.filter(retailer=retailer_code, status='converted').count()

        # 비에띠
        elif retailer_code == "IT-V-02":  # VIETTI
            from shop.api.dresscode.vietti.vietti import run_vietti_collection
            from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer, sync_soldout_products_from_raw

            fetch_count = run_vietti_collection()

            bulk_convert_or_update_products_by_retailer(retailer_code)

            sync_soldout_products_from_raw(retailer_code)
            print(f"🔁 비에띠 품절 반영 완료: {retailer_code}")

            register_count = RawProduct.objects.filter(retailer=retailer_code, status='converted').count()                


    #아뜰리에

        # 쿠쿠이니
        elif retailer_code == "IT-C-02":
            from shop.api.atelier.convert_cuccuini_products import convert_atelier_products
            from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer, sync_soldout_products_from_raw

            print("🟡 [1/3] CUCCUINI 상품 수집 및 저장 시작")
            fetch_count = convert_atelier_products()

            print("🟡 [2/3] 가공상품 등록 시작")
            register_count = bulk_convert_or_update_products_by_retailer(retailer_code)

            print("🟡 [3/3] 상품 솔드아웃")
            sync_soldout_products_from_raw(retailer_code)

            print(f"✅ CUCCUINI 전체 프로세스 완료 - 수집: {fetch_count}개 / 등록: {register_count}개")


             
        # 비니실비아
        elif retailer_code == "IT-B-02":
            from shop.api.atelier.convert_bini_products import convert_atelier_products
            from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer, sync_soldout_products_from_raw

            print("🟡 [1/3] bini 상품 수집 및 저장 시작")
            fetch_count = convert_atelier_products()

            print("🟡 [2/3] 가공상품 등록 시작")
            register_count = bulk_convert_or_update_products_by_retailer(retailer_code)

            print("🟡 [3/3] 상품 솔드아웃")
            sync_soldout_products_from_raw(retailer_code)

            print(f"✅ bini 전체 프로세스 완료 - 수집: {fetch_count}개 / 등록: {register_count}개")


        # 미네띠
        elif retailer_code == "IT-M-01":
            from shop.api.atelier.convert_minetti_products import convert_atelier_products
            from shop.services.product.conversion_service import bulk_convert_or_update_products_by_retailer, sync_soldout_products_from_raw

            print("🟡 [1/3] MINETTI 상품 수집 및 저장 시작")
            fetch_count = convert_atelier_products()

            print("🟡 [2/3] 가공상품 등록 시작")
            register_count = bulk_convert_or_update_products_by_retailer(retailer_code)

            print("🟡 [3/3] 상품 솔드아웃")
            sync_soldout_products_from_raw(retailer_code)

            print(f"✅ MINETTI 전체 프로세스 완료 - 수집: {fetch_count}개 / 등록: {register_count}개")



        # 완료 시간 및 수량 기록
        retailer.last_fetch_finished_at = timezone.now()
        retailer.last_register_finished_at = timezone.now()
        retailer.last_fetched_count = fetch_count or 0         # ✅ None 방지
        retailer.last_registered_count = register_count or 0   # ✅ None 방지
        retailer.is_running = False
        retailer.save()



        

    except Exception as e:
        print(f"❌ 파이프라인 실행 중 오류: {e}")
        # 에러를 로그로 남기되 return은 살림
    finally:
        retailer.is_running = False
        try:
            retailer.save()
        except Exception as save_error:
            print(f"❌ Retailer 저장 실패 (finally): {save_error}")


    return fetch_count, register_count        

    

