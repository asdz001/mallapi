from eventlog.models import ConversionLog

def log_conversion_failure(raw_product, reason, source="conversion"):
    """
    상품 등록 실패 시 호출되는 공통 로깅 함수

    - raw_product: 실패한 원본 상품
    - reason: 실패 사유 (예: 브랜드 치환 실패)
    - source: 실패 출처 구분 ('conversion', 'api_fetch' 등)
    """
    ConversionLog.objects.create(
        raw_product=raw_product,
        retailer=raw_product.retailer,  # ✅ 거래처 정보도 함께 저장
        reason=reason,
        source=source
    )
