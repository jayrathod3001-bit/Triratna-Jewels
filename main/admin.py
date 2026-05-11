from django.contrib import admin
from .models import (
    Banner, Jewellery, RegisterUser, MetalPrice, WishlistItem, 
    CartItem, NewsletterSubscriber, SiteSetting, Order, OrderItem, 
    StaffUser, CancelledOrder, ProductReview
)

admin.site.register(Banner)
@admin.register(RegisterUser)
class RegisterUserAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone_number')
    search_fields = ('first_name', 'last_name', 'email', 'phone_number')
admin.site.register(WishlistItem)
admin.site.register(CartItem)
admin.site.register(NewsletterSubscriber)
admin.site.register(SiteSetting)


@admin.register(Jewellery)
class JewelleryAdmin(admin.ModelAdmin):
    list_display = ('name', 'material_type', 'karat', 'weight', 'current_price', 'stock_quantity', 'is_in_stock', 'is_featured', 'is_best_seller', 'is_recommended')
    list_editable = ('is_featured', 'is_best_seller', 'is_recommended', 'is_in_stock')
    list_filter = ('material_type', 'karat', 'is_in_stock', 'is_featured', 'is_best_seller', 'is_recommended')
    search_fields = ('name',)
    # price is not editable because it is auto-calculated
    readonly_fields = ('price', 'current_price')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'type', 'image', 'is_featured', 'is_best_seller', 'is_recommended')
        }),
        ('Material Specifications', {
            'fields': ('material_type', 'karat', 'weight', 'manual_rate', 'price', 'current_price')
        }),
        ('Inventory Management', {
            'fields': ('stock_quantity', 'is_in_stock')
        }),
    )

@admin.register(MetalPrice)
class MetalPriceAdmin(admin.ModelAdmin):
    list_display = ("gold_price", "silver_price", "updated_at")

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'base_amount', 'making_charges', 'gst_amount', 'total_amount', 'payment_method', 'is_paid', 'order_date')
    list_filter = ('is_paid', 'payment_method', 'order_date')
    inlines = [OrderItemInline]
    readonly_fields = ('base_amount', 'making_charges', 'gst_amount', 'total_amount', 'order_date')

@admin.register(StaffUser)
class StaffUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('name', 'email')

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('jewellery', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')

@admin.register(CancelledOrder)
class CancelledOrderAdmin(admin.ModelAdmin):
    list_display = ('original_order_id', 'user', 'base_amount', 'making_charges', 'gst_amount', 'total_amount', 'refund_amount', 'cancellation_charge', 'cancelled_at')
    list_filter = ('cancelled_at',)
    readonly_fields = ('original_order_id', 'user', 'base_amount', 'making_charges', 'gst_amount', 'total_amount', 'refund_amount', 'cancellation_charge', 'charge_percentage', 'payment_method', 'order_date', 'cancelled_at', 'items_data')
