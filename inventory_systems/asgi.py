"""
ASGI config for inventory_systems project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory_systems.settings')

# inventory_systems/wsgi.py
import django
django.setup()
from inventory_systems.startup import ensure_afam_tenant
ensure_afam_tenant()


application = get_asgi_application()
