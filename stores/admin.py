from django.contrib import admin
from .models import Store, Product, Order, OrderItem


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'created_at']
    list_filter = ['created_at', 'owner']
    search_fields = ['name', 'owner__username']
    readonly_fields = ['created_at', 'updated_at']
    

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'price', 'stock', 'created_at']
    list_filter = ['store', 'created_at']
    search_fields = ['name', 'store__name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['price', 'stock']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'store', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'store', 'created_at']
    search_fields = ['customer__username', 'store__name']
    readonly_fields = ['customer', 'store', 'total_amount', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    
    def has_add_permission(self, request):
        return False  # Orders should only be created through API
