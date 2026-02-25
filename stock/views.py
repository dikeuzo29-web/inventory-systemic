from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Category, Product, Transaction, Sale
from .serializers import CategorySerializer, ProductSerializer, TransactionSerializer, SaleSerializer
from .permissions import IsCashierOrManager, IsManager
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CategoryForm, ProductForm, SalesTransactionForm, RestockTransactionForm, BottleReturnForm
from django.db import transaction
from django.contrib import messages
from accounts.models import CustomUser
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import F
import json
from django.forms import modelformset_factory
from django.db import transaction as db_transaction
from .models import SaleItem


from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Category, Product, Transaction, Sale, SaleItem
from .serializers import CategorySerializer, ProductSerializer, TransactionSerializer
from .permissions import IsCashierOrManager, IsManager
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import (
    CategoryForm,
    ProductForm,
    SalesTransactionForm,
    RestockTransactionForm,
    BottleReturnForm,
)
from django.db import transaction
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F
from django.forms import modelformset_factory
from django.db import transaction as db_transaction


def is_cashier_or_manager(user):
    return user.role in ["cashier", "manager"]


# =========================================================
# TENANT QUERYSET MIXIN
# =========================================================
class TenantQuerysetMixin:
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return super().get_queryset()
        return super().get_queryset().filter(tenant=user.company)


# =========================================================
# VIEWSETS (API)
# =========================================================
class CategoryViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsManager]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.company)


class ProductViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsManager]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.company)


class SalesTransactionViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    queryset = Sale.objects.prefetch_related("items__product").all()
    serializer_class = SaleSerializer
    permission_classes = [IsCashierOrManager]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.company, created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['transaction_type'] = 'sale'
        product_id = data.get("product")
        quantity = int(data.get("quantity", 0))

        try:
            product = Product.objects.get(
                id=product_id,
                tenant=request.user.company
            )
        except Product.DoesNotExist:
            return Response(
                {"detail": "Product not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if product.quantity < quantity:
            return Response(
                {"detail": "Insufficient stock for sale."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()


        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RestockTransactionViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsManager]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.company)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data["transaction_type"] = "restock"

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            created_by=request.user,
            tenant=request.user.company
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)


# =========================================================
# TEMPLATE VIEWS
# =========================================================
@login_required
def manage_categories(request):
    if request.user.role != "manager":
        return redirect("dashboard")

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.tenant = request.user.company
            category.save()
            return redirect("manage_categories")
    else:
        form = CategoryForm()

    categories = Category.objects.filter(
        tenant=request.user.company
    ).order_by("name")

    return render(
        request,
        "stock/manage_categories.html",
        {"form": form, "categories": categories},
    )


@login_required
def manage_products(request):
    if request.user.role != "manager":
        return redirect("dashboard")

    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.tenant = request.user.company
            product.save()
            return redirect("manage_products")
    else:
        form = ProductForm()

    products = Product.objects.filter(
        tenant=request.user.company
    ).order_by("name")

    paginator = Paginator(products, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    categories = Category.objects.filter(
        tenant=request.user.company
    )

    return render(
        request,
        "stock/manage_products.html",
        {
            "form": form,
            "products": products,
            "page_obj": page_obj,
            "categories": categories,
        },
    )


@login_required
def manage_sales(request):
    if request.user.role not in ["cashier", "manager"]:
        return redirect("dashboard")

    SalesFormSet = modelformset_factory(
        Transaction,
        form=SalesTransactionForm,
        extra=1,
        can_delete=True,
    )

    if request.method == "POST":
        formset = SalesFormSet(
            request.POST,
            queryset=Transaction.objects.none(),
            form_kwargs={"user": request.user},  # ✅ IMPORTANT
        )

        if formset.is_valid():
            try:
                with db_transaction.atomic():
                    sale = Sale.objects.create(
                        tenant=request.user.company,
                        created_by=request.user,
                    )

                    total = 0

                    for form in formset:
                        if not form.cleaned_data:
                            continue

                        product = Product.objects.select_for_update().get(
                            pk=form.cleaned_data["product"].pk,
                            tenant=request.user.company
                        )

                        quantity = form.cleaned_data["quantity"]

                        if product.quantity < quantity:
                            raise ValueError(
                                f"Insufficient stock for {product.name}"
                            )

                        item = SaleItem.objects.create(
                            sale=sale,
                            product=product,
                            quantity=quantity,
                            price=product.price,
                            deposit_amount=product.deposit_amount,
                            subtotal=(product.price + product.deposit_amount) * quantity,
                        )

                        Transaction.objects.create(
                            tenant=request.user.company,
                            product=product,
                            quantity=quantity,
                            transaction_type="sale",
                            created_by=request.user,
                        )

                        total += item.subtotal

                    sale.total_amount = total
                    sale.save()

                    return render(
                        request,
                        "stock/sales_receipt.html",
                        {"sale": sale},
                    )

            except Exception as e:
                messages.error(request, str(e))

    else:
        formset = SalesFormSet(
            queryset=Transaction.objects.none(),
            form_kwargs={"user": request.user},  # ✅ IMPORTANT
        )

    sales = Sale.objects.filter(
        tenant=request.user.company
    ).order_by("-timestamp")[:50]

    transactions = Transaction.objects.filter(
        tenant=request.user.company,
        transaction_type="sale",
    ).order_by("-timestamp")[:20]

    return render(
        request,
        "stock/manage_sales.html",
        {
            "formset": formset,
            "transactions": transactions,
            "sales": sales,
        },
    )


@login_required
@user_passes_test(is_cashier_or_manager, login_url="dashboard")
def manage_bottle_returns(request):

    if request.method == "POST":
        form = BottleReturnForm(
            request.POST,
            user=request.user  # ✅ IMPORTANT
        )

        if form.is_valid():
            with transaction.atomic():
                return_trans = form.save(commit=False)
                return_trans.transaction_type = "deposit_refund"
                return_trans.created_by = request.user
                return_trans.tenant = request.user.company

                product = Product.objects.select_for_update().get(
                    pk=return_trans.product.pk,
                    tenant=request.user.company
                )

                refund_amount = return_trans.quantity * product.deposit_amount

                return_trans.amount = -refund_amount
                return_trans.deposit_amount = product.deposit_amount
                return_trans.save()

                product.bottles_outstanding -= return_trans.quantity
                product.save()

                return redirect("manage_bottle_returns")
    else:
        form = BottleReturnForm(user=request.user)  # ✅ IMPORTANT

    recent_returns = Transaction.objects.filter(
        tenant=request.user.company,
        transaction_type="deposit_refund",
    ).order_by("-timestamp")[:20]

    return render(
        request,
        "stock/manage_bottle_returns.html",
        {
            "form": form,
            "recent_returns": recent_returns,
        },
    )


@login_required
def manage_restock(request):
    if request.user.role != "manager":
        return redirect("dashboard")

    if request.method == "POST":
        form = RestockTransactionForm(
            request.POST,
            user=request.user  # if you add filtering inside form
        )
        if form.is_valid():
            with transaction.atomic():
                restock = form.save(commit=False)
                restock.tenant = request.user.company
                restock.transaction_type = "restock"
                restock.created_by = request.user
                restock.save()
                return redirect("manage_restock")
    else:
        form = RestockTransactionForm(user=request.user)

    transactions = Transaction.objects.filter(
        tenant=request.user.company,
        transaction_type="restock",
    ).order_by("-timestamp")

    return render(
        request,
        "stock/manage_restock.html",
        {"form": form, "transactions": transactions},
    )

class SalesTransactionAPIView(APIView):
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = 'stock/manage_sales.html'

    def get(self, request, format=None):
        transactions = Transaction.objects.filter(
            tenant=request.user.company,
            transaction_type='sale'
        ).order_by('-timestamp')

        serializer = TransactionSerializer(transactions, many=True)
        form = SalesTransactionForm(user=request.user)

        return Response(
            {'transactions': serializer.data, 'form': form},
            template_name=self.template_name
        )

    def post(self, request, format=None):
        serializer = TransactionSerializer(data=request.data)

        if serializer.is_valid():
            product = serializer.validated_data['product']
            quantity = serializer.validated_data['quantity']

            if product.tenant != request.user.company:
                return Response(
                    {'detail': 'Unauthorized product access.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if product.quantity < quantity:
                form = SalesTransactionForm(
                    data=request.data,
                    user=request.user
                )
                form.add_error('quantity', 'Insufficient stock for sale.')

                transactions = Transaction.objects.filter(
                    tenant=request.user.company,
                    transaction_type='sale'
                ).order_by('-timestamp')

                return Response(
                    {
                        'transactions': TransactionSerializer(transactions, many=True).data,
                        'form': form
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                    template_name=self.template_name
                )

            serializer.save(
                transaction_type='sale',
                created_by=request.user,
                tenant=request.user.company
            )

            product.quantity -= quantity
            product.save()

            return redirect(request.path)

        else:
            form = SalesTransactionForm(
                data=request.data,
                user=request.user
            )

            transactions = Transaction.objects.filter(
                tenant=request.user.company,
                transaction_type='sale'
            ).order_by('-timestamp')

            return Response(
                {
                    'transactions': TransactionSerializer(transactions, many=True).data,
                    'form': form,
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST,
                template_name=self.template_name
            )