from django.db import models

class ConversionLog(models.Model):
    raw_product = models.ForeignKey("shop.RawProduct", on_delete=models.CASCADE)
    retailer = models.CharField(max_length=100, verbose_name="거래처")  # ✅ 추가
    source = models.CharField(max_length=50, default="conversion", verbose_name="출처")
    reason = models.TextField(verbose_name="실패 사유")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "실패 로그"
        verbose_name_plural = "3. 가공 실패 로그"

    def __str__(self):
        return f"[{self.source}] {self.retailer} - {self.raw_product.id} - {self.reason[:30]}"
