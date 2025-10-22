"""
WSGI config for inventory_systems project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory_systems.settings')

django.setup()

from inventory_systems.startup import ensure_afam_tenant
ensure_afam_tenant()  # ✅ create tenant if missing

application = get_wsgi_application()
