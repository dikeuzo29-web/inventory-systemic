# stock/serializers.py
from rest_framework import serializers
from .models import Category, Product, Transaction

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
