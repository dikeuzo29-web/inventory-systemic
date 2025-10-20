from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Category, Product, Transaction
from .serializers import CategorySerializer, ProductSerializer, TransactionSerializer
from .permissions import IsCashierOrManager, IsManager
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CategoryForm, ProductForm, SalesTransactionForm, RestockTransactionForm, BottleReturnForm
from django.db import transaction
from django.contrib import messages
from accounts.models import CustomUser
from django.core.paginator import Paginator
import uuid
from django.db.models import Sum, F, Count, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
import json
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import connection

def is_cashier_or_manager(user):
    return user.role in ['cashier', 'manager']

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsManager]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsManager]  # For product management, restrict to managers

# Sales Transaction endpoint – available to cashiers and managers
class SalesTransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsCashierOrManager]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['transaction_type'] = 'sale'
        product_id = data.get('product')
        quantity = int(data.get('quantity', 0))
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found.'}, status=status.HTTP_400_BAD_REQUEST)
        # Check if product has sufficient stock for the sale
        if product.quantity < quantity:
            return Response({'detail': 'Insufficient stock for sale.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

# Restock Transaction endpoint – available only to managers
class RestockTransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsManager]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['transaction_type'] = 'restock'
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

@login_required
def manage_categories(request):
    if request.user.role != 'manager':
        messages.warning(request, "You don't have permission to access this page.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.tenant = connection.tenant  # 👈 or however your user is linked
            category.save()
            messages.success(request, f"Category '{form.cleaned_data['name']}' created successfully.")
            return redirect('manage_categories')
    else:
        form = CategoryForm()

    categories = Category.objects.all().order_by('name')
    context = {'form': form, 'categories': categories}
    return render(request, 'stock/manage_categories.html', context)

@login_required
def manage_products(request):
    # Restrict access to managers only
    if request.user.role != CustomUser.ROLE_CHOICES[0][0]:  # safer than hardcoding 'manager'
        messages.warning(request, "You don't have permission to access this page.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.tenant = connection.tenant  # 👈 or however your user is linked
            product.save()
            print(f"Product saved: {Product.name}")
            messages.success(request, f"Product '{Product.name}' created successfully.")
            return redirect('manage_products')
    else:
        form = ProductForm()

    products = Product.objects.all().order_by('name')
    # Filtering
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    low_stock = request.GET.get('low_stock')
    if low_stock == 'true':
        products = products.filter(quantity__lte=F('low_stock_threshold'))

    # Sorting
    sort_by = request.GET.get('sort_by', 'name')
    order = request.GET.get('order', 'asc')
    if sort_by not in ['name', 'quantity', 'price', 'category']:
        sort_by = 'name'
    if order not in ['asc', 'desc']:
        order = 'asc'

    if sort_by == 'category':
        sort_by = 'category__name'
    if order == 'desc':
        sort_by = '-' + sort_by

    products = products.order_by(sort_by)

    # Pagination
    paginator = Paginator(products, 10)  # 10 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()
    context = {
        'form': form,
        'products': products,
        'page_obj': page_obj,
        'categories': categories,
    }
    return render(request, 'stock/manage_products.html', context)



# --- UPDATED manage_sales view ---
@login_required
def manage_sales(request):
    if request.user.role not in ['cashier', 'manager']:
        messages.warning(request, "You don't have permission to access this page.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = SalesTransactionForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.tenant = connection.tenant  # tenant-aware
            sale.transaction_type = 'sale'
            sale.created_by = request.user

            product = sale.product

            # ✅ Validate stock before saving (signal will only fire if valid)
            if product.quantity < sale.quantity:
                form.add_error('quantity', 'Insufficient stock for this sale.')
            else:
                sale.save()  # signal will now adjust stock
                messages.success(
                    request,
                    f"Sale of {sale.quantity} x {product.name} recorded."
                )
                return render(request, 'stock/sales_receipt.html', {'sale': sale})
    else:
        form = SalesTransactionForm()

    transactions = Transaction.objects.filter(
        transaction_type='sale'
    ).select_related('product', 'created_by').order_by('-timestamp')[:50]

    context = {'form': form, 'transactions': transactions}
    return render(request, 'stock/manage_sales.html', context)




@login_required
@user_passes_test(is_cashier_or_manager, login_url='dashboard')
def manage_bottle_returns(request):
    if request.method == 'POST':
        form = BottleReturnForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    return_trans = form.save(commit=False)
                    return_trans.transaction_type = 'deposit_refund'
                    return_trans.created_by = request.user
                    return_trans.tenant = connection.tenant

                    product = return_trans.product
                    
                    # Calculate refund amount
                    refund_amount = return_trans.quantity * product.deposit_amount
                    return_trans.amount = -refund_amount
                    return_trans.deposit_amount = product.deposit_amount
                    return_trans.save()
                    
                    # Update product
                    product.bottles_outstanding -= return_trans.quantity
                    product.save()

                    messages.success(
                        request, 
                        f"Processed return of {return_trans.quantity} {product.name}. "
                        f"Refunded: ₦{refund_amount:,.2f}"
                    )
                    return redirect('manage_bottle_returns')
                    
            except Exception as e:
                messages.error(request, f"Error processing return: {str(e)}")
        else:
            # Add form errors to messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = BottleReturnForm()

    # Pick default product (either selected in form or first available)
    product = form.initial.get('product') or form['product'].field.queryset.first()
    product_data = None
    if product:
        product_data = {
            'id': product.id,
            'bottles_outstanding': product.bottles_outstanding,
            'deposit_amount': product.deposit_amount,
        }

    recent_returns = Transaction.objects.filter(
        transaction_type='deposit_refund'
    ).select_related('product', 'created_by').order_by('-timestamp')[:20]

    return render(request, 'stock/manage_bottle_returns.html', {
        'form': form,
        'recent_returns': recent_returns,
        'product_data': product_data,
    })

@login_required
def manage_restock(request):
    """
    HTML view for recording restock transactions.
    Only managers are allowed to restock.
    Automatically increments product stock if restock is successful.
    """
    if request.user.role != 'manager':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RestockTransactionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                restock = form.save(commit=False)
                restock.tenant = connection.tenant
                restock.transaction_type = 'restock'
                restock.created_by = request.user
                restock.save()
                product = restock.product
                # Automatic stock balancing: add restocked quantity.
                product.quantity += restock.quantity
                #product.save()
                return redirect('manage_restock')
    else:
        form = RestockTransactionForm()
    
    transactions = Transaction.objects.filter(transaction_type='restock').order_by('-timestamp')
    context = {
        'form': form,
        'transactions': transactions,
    }
    return render(request, 'stock/manage_restock.html', context)

# stock/api_views.py

class SalesTransactionAPIView(APIView):
    """
    This view returns a list of sales transactions and renders an HTML form when requested.
    It accepts GET (to list transactions and display the form) and POST (to create a new sale).
    """
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'stock/manage_sales.html'
    
    def get(self, request, format=None):
        # Retrieve all sales transactions (ordered by most recent)
        transactions = Transaction.objects.filter(transaction_type='sale').order_by('-timestamp')
        serializer = TransactionSerializer(transactions, many=True)
        # Prepare a blank Django form for HTML form rendering.
        form = SalesTransactionForm()
        return Response({
            'transactions': serializer.data,
            'form': form
        }, template_name=self.template_name)
    
    def post(self, request, format=None):
        # When posted from an HTML form, the data is in request.data (or request.POST)
        # First try the DRF serializer
        serializer = TransactionSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.validated_data['product']
            quantity = serializer.validated_data['quantity']
            # Check if there is sufficient stock for a sale.
            if product.quantity < quantity:
                # If not enough stock, either re-render with an error or return JSON error.
                error_msg = 'Insufficient stock for sale.'
                # For HTML form rendering, re-render with the error in the form.
                form = SalesTransactionForm(data=request.data)
                form.add_error('quantity', error_msg)
                transactions = Transaction.objects.filter(transaction_type='sale').order_by('-timestamp')
                serializer_list = TransactionSerializer(transactions, many=True)
                return Response({
                    'transactions': serializer_list.data,
                    'form': form
                }, status=status.HTTP_400_BAD_REQUEST, template_name=self.template_name)
            # Save the transaction with transaction_type fixed to 'sale' and created_by from request.user.
            transaction = serializer.save(transaction_type='sale', created_by=request.user)
            # Update the product stock.
            product.quantity -= quantity
            product.save()
            # Return the created transaction. For HTML rendering, you might redirect to GET.
            # Here we redirect so that the form is cleared.
            return redirect(request.path)
        else:
            # If serializer errors occur, re-render the HTML form.
            form = SalesTransactionForm(data=request.data)
            transactions = Transaction.objects.filter(transaction_type='sale').order_by('-timestamp')
            serializer_list = TransactionSerializer(transactions, many=True)
            return Response({
                'transactions': serializer_list.data,
                'form': form,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST, template_name=self.template_name)
