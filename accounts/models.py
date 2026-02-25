# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from tenants.models import Client

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('manager', 'Manager'),
        ('cashier', 'Cashier'),
        ('warehouse', 'Warehouse Staff'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='manager')
    company = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        # null=True,
        # blank=True,
        related_name='users',
        help_text="The tenant (company) this user belongs to."
    )

    def __str__(self):
        return f"{self.username} ({self.company.name if self.company else 'No Company'})"