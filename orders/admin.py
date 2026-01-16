from django.contrib import admin
from .models import Order, OrderItem
from .models import Product
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product_id",
        "product_name",
        "price",
        "quantity",
        "line_total",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "total_amount",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    list_editable = ("status",)
    search_fields = ("id", "user__username")
    inlines = [OrderItemInline]
    readonly_fields = ("total_amount", "created_at")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "product_name",
        "price",
        "quantity",
        "line_total",
    )
    readonly_fields = ("line_total",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "inventory")
    search_fields = ("name",)


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def clear_product_master_cache(sender, **kwargs):
    cache.delete("product_master")
