# inventory_systems/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.shortcuts import render
from django.views.generic import TemplateView
from django.views.generic import RedirectView

def homepage(request):
    return render(request, "stock/homepage.html")

urlpatterns = [
    # Public homepage
    path("", homepage, name="home"),

    # ✅ ENABLE SUBFOLDER TENANTS
    path(
        f"{settings.TENANT_SUBFOLDER_PREFIX}/",
        include(settings.TENANT_URLCONF),
    ),

    # Public APIs
    path("api/accounts/", include("accounts.urls")),
    path("api/stock/", include("stock.urls")),

    # PWA + offline
    path("offline/", TemplateView.as_view(template_name="offline.html")),

    # Admin
    path("admin/", admin.site.urls),
]

#     path("", include("pwa.urls")),                                  # PWA routes
# ]
