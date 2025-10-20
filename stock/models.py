from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings
import uuid
from decimal import Decimal
from django.db import connection
from django_tenants.utils import get_public_schema_name

class Category(models.Model):
    """
    Represents a product category.
    """

    tenant = models.ForeignKey(
        settings.TENANT_MODEL,
        on_delete=models.CASCADE,
        related_name="categories"
    )
    name = models.CharField(
        max_length=255,
        help_text="Enter the category name (e.g. Electronics, Groceries)."
    )

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='unique_tenant_category')
        ]

    def save(self, *args, **kwargs):
        if not self.tenant_id and hasattr(connection, "tenant"):
            if connection.tenant.schema_name != get_public_schema_name():
                self.tenant = connection.tenant
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    """
    Represents a product with its details.
    """

    tenant = models.ForeignKey(
        settings.TENANT_MODEL,
        on_delete=models.CASCADE,
        related_name="products"
    )
    name = models.CharField(max_length=255, help_text="Enter the product name.")
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        help_text="Select the category for this product."
    )
    quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Enter the current stock level."
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Enter the price of the product."
    )
    expiry_date = models.DateField(blank=True, null=True)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    sku = models.CharField(max_length=20, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_returnable = models.BooleanField(default=False)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    bottles_outstanding = models.IntegerField(default=0, editable=False)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'sku'], name='unique_tenant_sku')
        ]

    # def save(self, *args, **kwargs):
    #     if not self.sku:
    #         self.sku = str(uuid.uuid4())[:20]
    #     super().save(*args, **kwargs)

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    def adjust_stock(self, delta):
        # self.quantity += delta  <-- This is the race condition
        # self.save()

        # This is the atomic, race-condition-safe way
        Product.objects.filter(pk=self.pk).update(quantity=F('quantity') + delta)
        self.refresh_from_db(fields=['quantity']) # Optional: update the current instance

    @property
    def total_price(self):
        return self.price + self.deposit_amount if self.is_returnable else self.price

    def save(self, *args, **kwargs):
        # Auto-generate SKU
        if not self.sku:
            self.sku = str(uuid.uuid4())[:20]

        # Auto-assign tenant if not set
        if not self.tenant_id and hasattr(connection, "tenant"):
            if connection.tenant.schema_name != get_public_schema_name():
                self.tenant = connection.tenant

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('sale', 'Sale'),
        ('restock', 'Restock'),
        ('deposit_refund', 'Deposit Refund'),
        ('deposit_collected', 'Deposit Collected'),
    )

    tenant = models.ForeignKey(
        settings.TENANT_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['transaction_type']),
        ]
        

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.product.name}"

    def save(self, *args, **kwargs):
        if self.transaction_type == 'sale':
            self.amount = Decimal(self.quantity) * self.product.price
            if self.product.is_returnable:
                self.deposit_amount = Decimal(self.quantity) * self.product.deposit_amount
        elif self.transaction_type == 'deposit_refund':
            self.amount = Decimal(self.quantity) * self.product.deposit_amount * Decimal('-1')
            self.deposit_amount = Decimal(self.quantity) * self.product.deposit_amount
        elif self.transaction_type == 'deposit_collected':
            self.deposit_amount = Decimal(self.quantity) * self.product.deposit_amount

         # Auto-assign tenant if not set
        if not self.tenant_id and hasattr(connection, "tenant"):
            if connection.tenant.schema_name != get_public_schema_name():
                self.tenant = connection.tenant

        super().save(*args, **kwargs)