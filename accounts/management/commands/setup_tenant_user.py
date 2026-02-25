from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from accounts.models import CustomUser
from tenants.models import Client
from stock.models import Category, Product, Sale, Transaction, SaleItem

class Command(BaseCommand):
    help = 'Setup tenant user with correct permissions'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument('password', type=str)
        parser.add_argument('tenant_name', type=str)
        parser.add_argument('--role', type=str, default='manager')

    def handle(self, *args, **options):
        tenant, _ = Client.objects.get_or_create(name=options['tenant_name'])
        
        user, created = CustomUser.objects.get_or_create(
            username=options['username'],
            defaults={'role': options['role'], 'company': tenant, 'is_staff': True}
        )
        
        if not created:
            user.company = tenant
            user.is_staff = True
            user.role = options['role']
        
        user.set_password(options['password'])

        for model in [Category, Product, Sale, Transaction, SaleItem]:
            ct = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(content_type=ct)
            user.user_permissions.add(*permissions)
        
        user.save()
        self.stdout.write(f"✅ User '{user.username}' setup for tenant '{tenant.name}'")