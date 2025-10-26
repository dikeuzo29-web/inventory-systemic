# stock/serializers.py
from rest_framework import serializers
from .models import Category, Product, Transaction

from rest_framework import serializers
from .models import Sale, Transaction

class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['product', 'quantity']

class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)

    class Meta:
        model = Sale
        fields = ['id', 'timestamp', 'total_amount', 'items', 'payment_method']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        tenant = getattr(connection, 'tenant', None)

        sale = Sale.objects.create(created_by=user, tenant=tenant, **validated_data)
        total = Decimal('0.00')

        for item in items_data:
            product = item['product']
            quantity = item['quantity']

            if product.quantity < quantity:
                raise serializers.ValidationError(
                    f"Insufficient stock for {product.name}."
                )

            txn = Transaction.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                transaction_type='sale',
                tenant=tenant,
                created_by=user
            )

            product.quantity -= quantity
            product.save(update_fields=['quantity'])
            total += txn.amount + txn.deposit_amount

        sale.total_amount = total
        sale.save(update_fields=['total_amount'])
        return sale


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'company']
        read_only_fields = ['company'] # Company is set by the view


class ProductSerializer(serializers.ModelSerializer):
    # This ensures that when creating/updating a product, the category provided
    # must belong to the user's company.
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), allow_null=True
    )

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['company'] # Company is set by the view

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically filter the category queryset based on the request user's company
        request = self.context.get('request')
        if request and hasattr(request.user, 'company'):
            self.fields['category'].queryset = Category.objects.filter(company=request.user.company)

        elif hasattr(request, 'tenant'):
            self.fields['category'].queryset = Category.objects.filter(
                tenant=request.tenant
            )


class TransactionSerializer(serializers.ModelSerializer):
    # This ensures the product provided in an API call belongs to the user's company.
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all()
    )
    
    class Meta:
        model = Transaction
        fields = ['id', 'product', 'quantity', 'transaction_type', 'timestamp', 'created_by', 'company', 'amount', 'deposit_amount']
        read_only_fields = ['transaction_type', 'timestamp', 'created_by', 'company', 'amount', 'deposit_amount']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request.user, 'company'):
            self.fields['product'].queryset = Product.objects.filter(company=request.user.company)
