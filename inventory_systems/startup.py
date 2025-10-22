# inventory_systems/startup.py
from tenants.models import Client, Domain
from django.db import connection

def ensure_afam_tenant():
    try:
        if not Client.objects.filter(schema_name="afam_drinks").exists():
            tenant = Client.objects.create(schema_name="afam_drinks", name="Afam Drinks")
            Domain.objects.create(
                domain="inventory-systemic.onrender.com",
                folder="afam_drinks",
                tenant=tenant,
                is_primary=True,
            )
            print("✅ Tenant 'afam_drinks' created successfully.")
        else:
            print("✅ Tenant 'afam_drinks' already exists.")
    except Exception as e:
        print(f"⚠️ Tenant check failed: {e}")
