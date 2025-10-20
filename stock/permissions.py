from rest_framework import permissions

class IsCashierOrManager(permissions.BasePermission):
    """
    Allows access only to users with role 'cashier' or 'manager'.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['manager', 'cashier']

class IsManager(permissions.BasePermission):
    """
    Only managers allowed.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'manager'
