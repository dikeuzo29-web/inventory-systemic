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
from django.http import FileResponse, HttpResponse
from django.views.decorators.http import require_GET

@require_GET
def sw(request):
    sw_path = BASE_DIR / 'static' / 'frontend' / 'sw.js'
    try:
        response = FileResponse(open(sw_path, 'rb'), content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        return response
    except FileNotFoundError:
        return HttpResponse('Not found', status=404)


def homepage(request):
    return render(request, "stock/homepage.html")

def chart_data(request):
    data = {
        "labels": ["Jan", "Feb", "Mar"],
        "values": [10, 20, 15],
    }
    return JsonResponse(data)



urlpatterns = [
    path("", homepage, name="home"),
    
    # PWA routes - ADD THES
   path('sw.js', sw), 
    path("offline/", TemplateView.as_view(template_name="offline.html"), name="offline"),
    
    # Public schema APIs
    path("api/accounts/", include("accounts.urls")),
    path("api/stock/", include("stock.urls")),
    path('api/chart-data/', chart_data, name='chart_data'),

    # Admin site
    path("admin/", admin.site.urls),
]
