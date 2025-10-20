# tenants/views.py
from django.http import HttpResponse
from .models import Client, Domain

def setup_initial_tenant(request):
    # Check if the tenant already exists to avoid errors
    if not Client.objects.filter(schema_name='itekton').exists():
        # Create the tenant client
        new_tenant = Client.objects.create(
            name='Itekton', 
            schema_name='itekton'
        )
    
        # Create the domain for it
        domain = Domain()
        domain.domain = 'itekton'  # The URL path
        domain.tenant = new_tenant
        domain.is_primary = True
        domain.save()
        
        return HttpResponse("<h1>Tenant 'Itekton' created successfully!</h1><p>You can now remove the setup URL from your code.</p>")
    else:
        return HttpResponse("<h1>Tenant 'itekton' already exists.</h1><p>You can now remove the setup URL from your code.</p>")

def create_tenant_superuser_view(request):
    # Tenant schema we want to create the user in
    tenant_schema = 'itekton'
    
    try:
        with schema_context(tenant_schema):
            # Check if the user already exists
            if CustomUser.objects.filter(username='admin').exists():
                return HttpResponse("Superuser 'admin' already exists in tenant 'itekton'.")
            
            # Create the superuser
            CustomUser.objects.create_superuser(
                username='admin', 
                email='admin@example.com', 
                password='admin12345'
            )
            return HttpResponse("<h1>Superuser 'admin' created for tenant 'itekton'!</h1><p>You can now log in.</p>")

    except Client.DoesNotExist:
        return HttpResponse(f"<h1>Tenant '{tenant_schema}' not found.</h1>")