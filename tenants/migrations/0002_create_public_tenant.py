# tenants/migrations/0002_create_public_tenant.py

from django.db import migrations

def create_public_tenant(apps, schema_editor):
    Client = apps.get_model('tenants', 'Client')
    Domain = apps.get_model('tenants', 'Domain')

    # Your Render domain name
    render_domain = 'inventory-systemic.onrender.com'

    # Check if the public tenant already exists
    if not Client.objects.filter(schema_name='public').exists():
        # Create the public tenant
        public_tenant = Client.objects.create(
            schema_name='public',
            name='Public Tenant'
            # Add any other required fields for your Client model here
        )

        # Create the domain associated with the public tenant
        Domain.objects.create(
            domain=render_domain,
            tenant=public_tenant,
            is_primary=True
        )
        print(f"Public tenant and domain '{render_domain}' created successfully!")
    else:
        print("Public tenant already exists.")


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),  # Make sure this matches your first tenants migration
    ]

    operations = [
        migrations.RunPython(create_public_tenant),
    ]
