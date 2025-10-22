from django.urls import path, include
from django.shortcuts import render, redirect

def tenant_home(request):
    return render(request, "stock/homepage.html")

urlpatterns = [
    path("", tenant_home, name="tenant_home"),                      # Tenant homepage
    path("api/accounts/", include("accounts.urls")),                # Tenant accounts
    path("api/stock/", include("stock.urls")),                      # Tenant stock API
    path("offline/", render, {"template_name": "offline.html"}),    # Optional offline page
    path("", include("pwa.urls")),                                  # PWA routes
]

