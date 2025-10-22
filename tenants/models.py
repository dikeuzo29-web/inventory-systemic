from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

class Client(TenantMixin):
    # Example fields (adjust based on your needs)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'tenants'

class Domain(DomainMixin):
    # Add this field for subfolder tenants
    domain = models.CharField(max_length=255)
    folder = models.CharField(max_length=100, unique=True, null=True, blank=True)

    def __str__(self):
        return f"{self.domain} ({self.folder or 'root'})"

    class Meta:
        app_label = 'tenants'
        unique_together = ('domain', 'folder') 
