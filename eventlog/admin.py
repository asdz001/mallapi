from django.contrib import admin
from eventlog.models import ConversionLog

@admin.register(ConversionLog)
class ConversionLogAdmin(admin.ModelAdmin):
    list_display = [ "retailer", "id", "source", "raw_product", "reason", "created_at"]
    search_fields = [ "retailer", "reason", "raw_product__product_name"]
    list_filter = [ "retailer", "source", "created_at"]
    readonly_fields = ["raw_product", "reason", "created_at", "source"]
