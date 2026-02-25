from tenants.models import Client

def ensure_afam_tenant():
    try:
        if not Client.objects.filter(name="Afam Drinks").exists():
            Client.objects.create(name="Afam Drinks")
            print("✅ Tenant 'Afam Drinks' created successfully.")
        else:
            print("✅ Tenant 'Afam Drinks' already exists.")
    except Exception as e:
        print(f"⚠️ Tenant check failed: {e}")