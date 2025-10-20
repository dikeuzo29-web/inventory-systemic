from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

class Client(TenantMixin):
    # Example fields (adjust based on your needs)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'tenants'

class Domain(DomainMixin):
    # Example fields (adjust based on your needs)
    domain = models.CharField(max_length=255, unique=True)

    class Meta:
        app_label = 'tenants'
