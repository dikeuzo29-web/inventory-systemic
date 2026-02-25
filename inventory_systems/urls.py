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

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.views.generic import TemplateView, RedirectView
from django.http import JsonResponse

def homepage(request):
    return render(request, "stock/homepage.html")

def chart_data(request):
    data = {"labels": ["Jan", "Feb", "Mar"], "values": [10, 20, 15]}
    return JsonResponse(data)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", homepage, name="home"),
    path("pwa/manifest.json", RedirectView.as_view(url="/static/pwa/manifest.json")),
    path("api/accounts/", include("accounts.urls")),
    path("api/stock/", include("stock.urls")),
    path('api/chart-data/', chart_data, name='chart_data'),
    path("offline/", TemplateView.as_view(template_name="offline.html"), name="offline"),
    path("", include("pwa.urls")),
]

