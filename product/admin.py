from django.contrib import admin

from .models import Product, ProductApplication, ProductTag, TagType

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
        "display_tags",
    )
    list_filter = ("publish", "valid", "completed", "start_time", "end_time")
    search_fields = ("item_name", "description", "user__username")
    readonly_fields = ("created_at",)
    
    def display_tags(self, obj):
        tag_names = obj.tags.values_list("tag_name", flat=True)
        return ", ".join(tag_names)

    display_tags.short_description = "タグ"


@admin.register(ProductApplication)
class ProductApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "apply_id",
        "product",
        "user",
        "quantity",
        "hope_time",
        "message",
        "apply_status",
        "apply_time",
    )
    list_filter = ("apply_status", "apply_time")
    search_fields = ("product__item_name", "user__username")
    readonly_fields = ("apply_time",)


@admin.register(TagType)
class TagTypeAdmin(admin.ModelAdmin):
    list_display = ("tag_id", "tag_name", "created_t")
    search_fields = ("tag_name",)
    ordering = ("tag_name",)


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "tag", "created_at")
    list_filter = ("tag",)
    search_fields = ("product__item_name", "tag__tag_name")
    autocomplete_fields = ("product", "tag")