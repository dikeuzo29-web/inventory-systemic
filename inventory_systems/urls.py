"""
URL configuration for inventory_systems project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# inventory_systems/urls.py

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.views.generic import TemplateView
from django.views.generic import RedirectView
import os
from django.conf import settings
from django.http import HttpResponse, JsonResponse

def homepage(request):
    return render(request, "stock/homepage.html")

def chart_data(request):
    data = {
        "labels": ["Jan", "Feb", "Mar"],
        "values": [10, 20, 15],
    }
    return JsonResponse(data)

def service_worker(request):
    try:
        # Read the service worker file
        sw_path = os.path.join(settings.BASE_DIR, 'static', 'serviceworker.js')
        with open(sw_path, 'r') as f:
            content = f.read()
        
        response = HttpResponse(content, content_type='application/javascript')
        # THIS IS THE KEY: Allow root scope
        response['Service-Worker-Allowed'] = '/'
        return response
    except FileNotFoundError:
        return HttpResponse('Service Worker not found', status=404)

def manifest_view(request):
    return render(request, 'pwa/manifest.json', content_type='application/manifest+json')

urlpatterns = [
    path("", homepage, name="home"),
    
    # PWA routes - ADD THESE
    path('pwa/manifest.json', RedirectView.as_view(url='/static/pwa/manifest.json')),
    path("offline/", TemplateView.as_view(template_name="offline.html"), name="offline"),
    
    # Public schema APIs
    path("api/accounts/", include("accounts.urls")),
    path("api/stock/", include("stock.urls")),
    path('api/chart-data/', chart_data, name='chart_data'),

    # PWA app (keep this if you're using django-pwa)
    path("", include("pwa.urls")),

    # Admin site
    path("admin/", admin.site.urls),
]
