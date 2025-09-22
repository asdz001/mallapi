# shop/signals.py

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# ✅ 기준 데이터 모델들 import
from dictionary.models import (
    BrandAlias,
    CategoryLevel1Alias, CategoryLevel2Alias,
    CategoryLevel3Alias, CategoryLevel4Alias,
)
from pricing.models import CountryAlias

# ✅ 캐시 리로드 함수 import
from shop.services.product.conversion_service import reload_conversion_cache

logger = logging.getLogger(__name__)


# 공통 시그널 함수
def _refresh_cache(sender, **kwargs):
    try:
        reload_conversion_cache()
        logger.info(f"[Signals] {sender.__name__} 변경 → 매핑 캐시 자동 리로드 성공")
    except Exception as e:
        logger.exception(f"[Signals] 매핑 캐시 리로드 실패: {e}")


# ✅ 브랜드/카테고리/국가 alias가 저장/삭제될 때마다 캐시 리로드
@receiver([post_save, post_delete], sender=BrandAlias)
@receiver([post_save, post_delete], sender=CategoryLevel1Alias)
@receiver([post_save, post_delete], sender=CategoryLevel2Alias)
@receiver([post_save, post_delete], sender=CategoryLevel3Alias)
@receiver([post_save, post_delete], sender=CategoryLevel4Alias)
@receiver([post_save, post_delete], sender=CountryAlias)
def refresh_mapping_cache(sender, **kwargs):
    _refresh_cache(sender, **kwargs)
