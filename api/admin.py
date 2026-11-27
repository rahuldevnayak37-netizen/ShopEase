from django.contrib import admin
from .models import (
    Product,
    Review,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Coupon,
    WishlistItem,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price",
        "stock",
        "category",
        "is_active",
        "is_featured",
    )
    list_filter = ("category", "is_active", "is_featured")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating")
    search_fields = ("name", "comment", "product__name")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "session_key", "created_at", "updated_at")
    search_fields = ("session_key",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "quantity", "unit_price")
    list_filter = ("product",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product",
        "product_name",
        "product_image",
        "quantity",
        "unit_price",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer_name",
        "total_amount",
        "payment_method",
        "payment_status",
        "status",
        "created_at",
    )
    list_filter = ("status", "payment_status", "payment_method", "created_at")
    search_fields = ("order_number", "customer_name", "email", "phone")
    readonly_fields = ("order_number", "created_at", "updated_at")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "quantity", "unit_price")
    search_fields = ("product_name",)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "discount_type",
        "discount_value",
        "minimum_order_amount",
        "usage_count",
        "usage_limit",
        "is_active",
        "valid_until",
    )
    list_filter = ("discount_type", "is_active")
    search_fields = ("code",)
    readonly_fields = ("usage_count", "created_at")


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("id", "session_key", "product", "created_at")
    search_fields = ("session_key", "product__name")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
