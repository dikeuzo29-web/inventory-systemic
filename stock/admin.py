from django.contrib import admin
from .models import Category, Product, Transaction, Sale, SaleItem

class TenantAdminMixin:
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(tenant=request.user.company)

    def save_model(self, request, obj, form, change):
        if not obj.tenant_id:
            obj.tenant = request.user.company
        super().save_model(request, obj, form, change)

@admin.register(Category)
class CategoryAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Product)
class ProductAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity', 'price', 'expiry_date', 'low_stock_threshold', 'is_low_stock', 'is_expired', 'bottles_outstanding')
    list_filter = ('category', 'expiry_date', 'is_returnable')
    search_fields = ('name', 'description')
    ordering = ('name',)

@admin.register(Sale)
class SaleAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'total_amount', 'payment_method', 'tenant')
    search_fields = ('id',)
    list_filter = ('payment_method',)

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'subtotal')
    search_fields = ('sale__id', 'product__name')

@admin.register(Transaction)
class TransactionAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('transaction_type', 'product', 'quantity', 'amount', 'timestamp', 'tenant')
    list_filter = ('transaction_type', 'timestamp', 'tenant')
    search_fields = ('product__name', 'notes')