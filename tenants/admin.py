# tenants/admin.py

from django.contrib import admin
from .models import Client

# This lets you create/edit tenants in the admin
admin.site.register(Client)
