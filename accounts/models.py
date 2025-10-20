# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django_tenants.utils import get_public_schema_name
from django.db import connection
from django.conf import settings

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('manager', 'Manager'),
        ('cashier', 'Cashier'),
        ('warehouse', 'Warehouse Staff'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='manager')
    # This ForeignKey is now correctly pointing to the main tenant model
    company = models.ForeignKey(
        settings.TENANT_MODEL, # Correctly uses the model from your settings
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="The tenant (company) this user belongs to."
    )

    def save(self, *args, **kwargs):
        """
        If a user is being created within a tenant context,
        automatically assign that tenant to the user's company field.
        """
        # Check if company is not set and we are in a tenant context
        if not self.company_id and hasattr(connection, 'tenant'):
            # Ensure we're not on the public schema
            if connection.tenant.schema_name != get_public_schema_name():
                # Directly assign the tenant object to the company field
                self.company = connection.tenant
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.company.name if self.company else 'No Company'})"