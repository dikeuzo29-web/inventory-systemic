from django import forms
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory
from .models import Category, Product, Transaction, SaleItem
from datetime import date


class ProductForm(forms.ModelForm):
    is_returnable = forms.TypedChoiceField(
        choices=[(True, 'Yes'), (False, 'No')],
        coerce=lambda x: x == 'True',
        widget=forms.RadioSelect,
        label="Is returnable?",
        initial=False
    )

    class Meta:
        model = Product
        exclude = ['tenant']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_deposit_amount(self):
        is_returnable = self.cleaned_data.get('is_returnable')
        deposit_amount = self.cleaned_data.get('deposit_amount')
        if is_returnable and deposit_amount <= 0:
            raise ValidationError("Deposit amount must be greater than 0 for returnable products.")
        if not is_returnable and deposit_amount != 0:
            raise ValidationError("Deposit amount must be 0 for non-returnable products.")
        return deposit_amount


class SalesTransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['product', 'quantity']
        widgets = {'quantity': forms.NumberInput(attrs={'min': 1})}

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['product'].queryset = Product.objects.filter(
                tenant=user.company, quantity__gt=0)
        else:
            self.fields['product'].queryset = Product.objects.none()

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        product = self.cleaned_data.get('product')
        if product and quantity > product.quantity:
            raise ValidationError(f"Only {product.quantity} units available in stock.")
        return quantity


class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity']
        widgets = {'quantity': forms.NumberInput(attrs={'min': 1})}

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['product'].queryset = Product.objects.filter(
                tenant=user.company, quantity__gt=0)
        else:
            self.fields['product'].queryset = Product.objects.none()

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        product = self.cleaned_data.get('product')
        if product and quantity > product.quantity:
            raise ValidationError(f"Only {product.quantity} units available in stock.")
        return quantity


SaleItemFormSet = modelformset_factory(
    SaleItem, form=SaleItemForm, extra=100, can_delete=False
)


class BottleReturnForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['product', 'quantity']
        widgets = {'quantity': forms.NumberInput(attrs={'min': 1})}

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        qs = Product.objects.filter(is_returnable=True, bottles_outstanding__gt=0)
        if user:
            qs = qs.filter(tenant=user.company)
        self.fields['product'].queryset = qs

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        product = self.cleaned_data.get('product')
        if product and quantity > product.bottles_outstanding:
            raise ValidationError(
                f"Only {product.bottles_outstanding} containers outstanding.")
        return quantity


class RestockTransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['product', 'quantity']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['product'].queryset = Product.objects.filter(
                tenant=user.company)
        else:
            self.fields['product'].queryset = Product.objects.none()


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter category name'}),
        }

# class ProductForm(forms.ModelForm):
#     expiry_date = forms.DateField(
#         required=False,
#         widget=forms.DateInput(attrs={'type': 'date'})
#     )

#     is_returnable = forms.TypedChoiceField(
#         choices=[(True, 'Yes'), (False, 'No')],
#         coerce=lambda x: x == 'True',
#         widget=forms.RadioSelect,
#         label="Is returnable?",
#         initial=False
#     )

#     class Meta:
#         model = Product
#         fields = [
#             'name', 'description', 'category', 'sku',
#             'quantity', 'price', 'low_stock_threshold',
#             'is_returnable',
#             'deposit_amount',
#             'expiry_date'
#         ]
#         widgets = {
#             'name': forms.TextInput(attrs={'placeholder': 'Enter product name'}),
#             'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter product description'}),
#             'price': forms.NumberInput(attrs={'min': 0.01, 'step': '0.01'}),
#             'quantity': forms.NumberInput(attrs={'min': 1}),
#             'low_stock_threshold': forms.NumberInput(attrs={'min': 0}),
#             'deposit_amount': forms.NumberInput(attrs={'min': 0.00, 'step': '0.01'}),
#         }

#     def clean_expiry_date(self):
#         expiry_date = self.cleaned_data.get('expiry_date')
#         if expiry_date and expiry_date < date.today():
#             raise ValidationError("Expiry date cannot be in the past.")
#         return expiry_date

# # ... (rest of your forms.py)
# class BottleReturnForm(forms.Form):
#     product = forms.ModelChoiceField(
#         queryset=Product.objects.filter(is_returnable=True),
#         label="Returned Bottle Type",
#         widget=forms.Select(attrs={'class': 'form-select'}),
#         empty_label="-- Select a returnable product --"
#     )
#     quantity = forms.IntegerField(
#         min_value=1,
#         label="Number of Empty Bottles Returned"
#     )

#     def clean(self):
#         cleaned_data = super().clean()
#         product = cleaned_data.get("product")
#         quantity = cleaned_data.get("quantity")

#         if product and quantity:
#             if quantity > product.bottles_outstanding:
#                 self.add_error('quantity', f"Cannot return {quantity} bottles; only {product.bottles_outstanding} are recorded as outstanding.")
        
#         return cleaned_data
