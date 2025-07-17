# pricing/services/season_updater.py

from shop.models import Product
from pricing.models import RetailerSeasonSummary

def update_retailer_season_summary():
    from collections import defaultdict

    data = defaultdict(set)

    # 중복 없이 수집
    qs = Product.objects.exclude(season__isnull=True).exclude(season="").values("retailer", "season").distinct()
    for row in qs:
        data[row["retailer"]].add(row["season"].strip())

    # 전체 초기화
    RetailerSeasonSummary.objects.all().delete()

    # 다시 저장
    for retailer_code, season_set in data.items():
        sorted_list = sorted(season_set)
        RetailerSeasonSummary.objects.create(
            retailer_code=retailer_code,
            seasons=",".join(sorted_list)
        )
