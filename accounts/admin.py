# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.conf import settings
from .models import CustomUser

# It's good practice to import the tenant model for type checking, though not strictly required
# This assumes your TENANT_MODEL is 'tenants.Client'
from tenants.models import Client as TenantModel 

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    # This correctly adds the 'company' field (which is a ForeignKey to the Tenant)
    # to the add/change forms.
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Tenant Info', {'fields': ('company',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('company',)}),
    )

    # Shows the company in the list view
    list_display = ('username', 'email', 'is_staff', 'company')

    # Allows filtering by company
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'company')
    
    search_fields = ('username', 'email')
    ordering = ('username',)

    # --- Your multi-tenancy logic is correct! ---
    # It will work as intended now that 'company' points to the tenant model.

    def get_queryset(self, request):
        """
        Restricts non-superusers to only see users from their own tenant.
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs # Superusers see all users
        
        # Regular staff users only see users from their own company/tenant
        if hasattr(request.user, 'company') and request.user.company:
            return qs.filter(company=request.user.company)
        return qs.none() # Or return empty if user has no company

    def save_model(self, request, obj, form, change):
        """
        Automatically assign the user's tenant when a new user is created
        by a non-superuser.
        """
        if not request.user.is_superuser and not obj.company_id:
            obj.company = request.user.company
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        """
        Makes the company field read-only for non-superusers.
        """
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if 'company' in form.base_fields:
                form.base_fields['company'].queryset = TenantModel.objects.filter(pk=request.user.company_id)
                form.base_fields['company'].initial = request.user.company
                form.base_fields['company'].disabled = True
        return form

# --- Important: Register the Tenant Admin ---
# For the 'company' dropdown to work nicely in the admin for superusers,
# you should also have an admin class for your tenant model.
# django-tenants provides a default one you can use.

from django_tenants.admin import TenantAdminMixin

@admin.register(TenantModel)
class TenantAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'schema_name', 'created_at')