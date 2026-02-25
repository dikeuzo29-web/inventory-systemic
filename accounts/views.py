from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout # Import the logout function
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.contrib import messages
from decimal import Decimal
from django.db.models import ExpressionWrapper, DecimalField, F, Sum, Count
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.utils import timezone
import json

from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer

from stock.models import Category, Product, Transaction
from stock.serializers import CategorySerializer, ProductSerializer, TransactionSerializer
from stock.forms import CategoryForm, ProductForm, SalesTransactionForm, RestockTransactionForm
from accounts.models import CustomUser
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta, time


def home(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    else:
        return redirect('accounts:login')

def login_page(request):
    # Prevent authenticated users from seeing the login page
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('accounts:dashboard')
        else:
            context = {'error': 'Invalid credentials'}
            return render(request, 'accounts/login.html', context)
    return render(request, 'accounts/login.html')

# Custom logout view
def custom_logout(request):
    """
    Logs the user out and redirects to the login page.
    """
    logout(request) # This is the core Django logout function
    # Redirect to the login page after successful logout
    return redirect('accounts:login')




@login_required(login_url='accounts:login')
def dashboard(request):
    # --- Date Filtering Logic (REFINED & FIXED) ---
    period = request.GET.get('period', 'monthly')
    now = timezone.now()
    
    # Use the server's current timezone for conversions
    tz = timezone.get_current_timezone()

    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if period == 'custom' and start_date_str and end_date_str:
        try:
            # Parse the date strings into date objects
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            # Create timezone-aware datetime objects for the beginning of the start day
            # and the beginning of the day AFTER the end day.
            start_datetime = datetime.combine(start_date, time.min).replace(tzinfo=tz)
            end_datetime = datetime.combine(end_date + timedelta(days=1), time.min).replace(tzinfo=tz)

        except (ValueError, TypeError):
            # If parsing fails, fall back to the default (monthly)
            period = 'monthly'
            start_datetime = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # If not custom, calculate the range
    if period != 'custom':
        if period == 'daily':
            start_datetime = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_datetime = start_datetime + timedelta(days=1)
        
        elif period == 'quarterly':
            current_quarter_start_month = 3 * ((now.month - 1) // 3) + 1
            start_datetime = now.replace(month=current_quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate end of quarter
            if start_datetime.month <= 9:
                end_datetime = start_datetime.replace(month=start_datetime.month + 3)
            else:
                end_datetime = start_datetime.replace(year=start_datetime.year + 1, month=1)

        else: # Default to 'monthly'
            start_datetime = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Calculate end of month
            if start_datetime.month == 12:
                end_datetime = start_datetime.replace(year=start_datetime.year + 1, month=1)
            else:
                end_datetime = start_datetime.replace(month=start_datetime.month + 1)

    # Filter transactions using the calculated timezone-aware datetime range
    transactions = Transaction.objects.filter(
        tenant=request.user.company,
        timestamp__gte=start_datetime,
        timestamp__lt=end_datetime,
        transaction_type='sale'
    )

    # --- Sales Performance Metrics ---
    revenue_expr = ExpressionWrapper(
        F('quantity') * F('product__price'),
        output_field=DecimalField()
    )
    
    sales_summary = transactions.aggregate(
        total_revenue=Coalesce(Sum(revenue_expr), Decimal(0)),
        total_quantity=Coalesce(Sum('quantity'), 0),
        transactions_count=Count('id')
    )

    # --- Current Inventory Status ---
    products = Product.objects.filter(tenant=request.user.company).order_by('name')
    current_stock_list = []
    total_inventory_value = Decimal(0)

    for product in products:
        inventory_value = product.quantity * product.price
        total_inventory_value += inventory_value
        status_info = 'In Stock'
        if product.quantity <= 0:
            status_info = 'Out of Stock'
        elif product.quantity <= product.low_stock_threshold:
            status_info = 'Low Stock'

        current_stock_list.append({
            'name': product.name,
            'quantity': product.quantity,
            'category': product.category.name if product.category else '-',
            'reorder_level': product.low_stock_threshold,
            'stock_status': status_info,
            'inventory_value': inventory_value,
            'last_updated': product.last_updated,
        })

    # --- Chart Data Preparation ---
    # 1. Sales Trend
    sales_trend_data = (
        transactions
        .annotate(date=TruncDate('timestamp', tzinfo=tz))  # Use current timezone
        .values('date')
        .annotate(
            total_sales=Coalesce(Sum('quantity'), 0),
            total_revenue=Coalesce(Sum(revenue_expr), Decimal(0))
        )
        .order_by('date')
    )

    sales_trend = {
        'dates': [item['date'].strftime('%b %d') for item in sales_trend_data],
        'quantities': [item['total_sales'] for item in sales_trend_data],
        'revenues': [float(item['total_revenue']) for item in sales_trend_data]
    }

    # 2. Inventory Value by Category
    value_expr = ExpressionWrapper(
        F('quantity') * F('price'),
        output_field=DecimalField()
    )
    
    category_value = (
        Product.objects.filter(tenant=request.user.company)
        .values('category__name')
        .annotate(total_value=Coalesce(Sum(value_expr), Decimal(0)))
        .order_by('-total_value')
    )
    
    inventory_by_category = {
        'labels': [item['category__name'] or 'Uncategorized' for item in category_value],
        'values': [float(item['total_value']) for item in category_value]
    }

    # 3. Top Selling Products - FIXED QUERY
    top_products_data = (
        transactions
        .values('product__name', 'product__id')
        .annotate(
            total_sold=Coalesce(Sum('quantity'), 0),
            total_revenue=Coalesce(Sum(revenue_expr), Decimal(0))
        )
        .order_by('-total_sold')[:5]
    )

    # Format top products data for chart
    top_products = {
        'labels': [item['product__name'] for item in top_products_data],
        'sales': [item['total_sold'] for item in top_products_data],
        'revenues': [float(item['total_revenue']) for item in top_products_data]
    }

    # Debug: Print top products to console
    print("Top Products Data:", list(top_products_data))
    print("Top Products Formatted:", top_products)

    chart_data = {
        'sales_trend': sales_trend,
        'inventory_by_category': inventory_by_category,
        'top_products': top_products  # Use the formatted dict instead of raw queryset
    }

    context = {
        'period': period,
        'current_stock': current_stock_list,
        'total_inventory_value': total_inventory_value,
        'total_revenue': sales_summary['total_revenue'],
        'total_quantity': sales_summary['total_quantity'],
        'transactions_count': sales_summary['transactions_count'],
        'chart_data': json.dumps(chart_data, default=str)  # Safe serialization
    }
    return render(request, 'accounts/dashboard.html', context)