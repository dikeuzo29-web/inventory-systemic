# stock/admin.py
from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'quantity', 'price',
        'expiry_date', 'low_stock_threshold', 'is_low_stock', 'is_expired','bottles_outstanding'
    )
    list_filter = ('category', 'expiry_date', 'is_returnable')
    search_fields = ('name', 'description')
    ordering = ('name',)

