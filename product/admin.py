from django.contrib import admin

from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "item_id",
        "item_name",
        "number",
        "start_time",
        "end_time",
        "publish",
        "valid",
        "completed",
        "user",
    )
    list_filter = ("publish", "valid", "completed", "start_time", "end_time")
    search_fields = ("item_name", "description", "user__username")
    readonly_fields = ("created_at",)
    
    def tags(self, obj):
        return ", ".join(tag.name for tag in obj.tags.all())