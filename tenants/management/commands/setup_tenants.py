from django.core.management import call_command, BaseCommand
from tenants.models import Client, Domain

class Command(BaseCommand):
    help = "Creates the initial public and itekton tenants and runs migrations."

    def handle(self, *args, **options):
        self.stdout.write(">>> SCRIPT STARTED: Setting up tenants and database...")

        try:
            # --- Define Details ---
            public_schema = 'public'
            tenant_schema = 'itekton'
            # NOTE: This domain name is for the initial setup.
            domain_name = 'web-production-6f92.up.railway.app' 

            # --- Create Public Tenant ---
            public_tenant, created = Client.objects.get_or_create(
                schema_name=public_schema,
                defaults={'name': 'Public Tenant'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"--- Public Tenant '{public_schema}' created."))
            else:
                self.stdout.write(f"--- Public Tenant '{public_schema}' already exists.")

            # --- Link Domain to Public Tenant ---
            domain, created = Domain.objects.get_or_create(
                domain=domain_name,
                tenant=public_tenant,
                defaults={'is_primary': True}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"--- Domain '{domain_name}' linked to public tenant."))
            else:
                self.stdout.write(f"--- Domain '{domain_name}' was already linked.")

            # --- Create 'itekton' Tenant ---
            itekton_tenant, created = Client.objects.get_or_create(
                schema_name=tenant_schema,
                defaults={'name': 'Itekton'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"--- Tenant '{tenant_schema}' created."))
            else:
                self.stdout.write(f"--- Tenant '{tenant_schema}' already exists.")

            # --- Run Migrations ---
            self.stdout.write("--- Running migrations for SHARED apps...")
            call_command('migrate_schemas', '--shared')
            self.stdout.write("--- Running migrations for TENANT apps...")
            call_command('migrate_schemas', '--tenant')
            self.stdout.write(self.style.SUCCESS("\n>>> SETUP COMPLETE! Your application is live."))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"\n!!! AN ERROR OCCURRED: {e}"))
