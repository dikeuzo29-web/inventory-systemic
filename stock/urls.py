from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import SimpleRouter
from .views import (
    CategoryViewSet, ProductViewSet,
    SalesTransactionViewSet, RestockTransactionViewSet,
    manage_categories, manage_products,
    manage_sales, manage_restock,
    SalesTransactionAPIView,
    manage_bottle_returns
)

router = SimpleRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'sales', SalesTransactionViewSet, basename='sales')
router.register(r'restock', RestockTransactionViewSet, basename='restock')

urlpatterns = [
    path('api', include(router.urls)),
    path('manage/categories/', manage_categories, name='manage_categories'),
    path('manage/products/', manage_products, name='manage_products'),
    path('sales/', manage_sales, name='manage_sales'),
    path('restock/', manage_restock, name='manage_restock'),
    path('returns/', manage_bottle_returns, name='manage_bottle_returns'),
    path('api/sales/', SalesTransactionAPIView.as_view(), name='api_sales'),
]
