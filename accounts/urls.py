# accounts/urls.py
from django.urls import path, include
from django.views.generic import TemplateView
from accounts.views import login_page, dashboard, custom_logout
app_name = 'accounts'

urlpatterns = [
    # Djoser authentication endpoints:
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    # redirect root → login
    path("login/", login_page, name="login"),
    path("logout/", custom_logout, name="logout"),
    path("dashboard/", dashboard, name="dashboard"),

]

