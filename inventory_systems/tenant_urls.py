# inventory_systems/tenant_urls.py
from django.urls import path, include
from django.shortcuts import render
from django.views.generic import TemplateView

def tenant_home(request):
    return render(request, "stock/homepage.html")

urlpatterns = [
    path("", tenant_home, name="tenant_home"),
    path("api/accounts/", include("accounts.urls")),
    path("api/stock/", include("stock.urls")),
    path("offline/", TemplateView.as_view(template_name="offline.html")),
]
