#!/bin/bash

# This script ensures the database is ready and then starts the server.

echo "--- Running database migrations and tenant setup ---"
python manage.py setup_tenants

echo "--- Starting Gunicorn web server ---"
gunicorn inventory_systems.wsgi --log-file -

