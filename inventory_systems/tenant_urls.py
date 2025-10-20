from django.urls import path
from django.shortcuts import redirect


def tenant_root_redirect(request):
    return redirect("login")

urlpatterns = [
    path("", tenant_root_redirect, name="tenant_root"),   
]
