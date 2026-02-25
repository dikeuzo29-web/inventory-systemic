from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser
from tenants.models import Client

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Tenant Info', {'fields': ('company', 'role')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('company', 'role')}),
    )
    list_display = ('username', 'email', 'is_staff', 'company', 'role')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'company', 'role')
    search_fields = ('username', 'email')
    ordering = ('username',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'company') and request.user.company:
            return qs.filter(company=request.user.company)
        return qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and not obj.company_id:
            obj.company = request.user.company
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if request.user.is_superuser:
            if 'company' in form.base_fields:
                form.base_fields['company'].required = True
                form.base_fields['company'].empty_label = "-- Select Company --"
        else:
            if 'company' in form.base_fields:
                form.base_fields['company'].queryset = Client.objects.filter(pk=request.user.company_id)
                form.base_fields['company'].initial = request.user.company
                form.base_fields['company'].disabled = True
        return form

@admin.register(Client)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')