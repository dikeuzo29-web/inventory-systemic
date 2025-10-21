# accounts/migrations/0002_create_superuser.py

import os
from django.db import migrations
from django.contrib.auth import get_user_model

def set_or_create_superuser(apps, schema_editor):
    User = get_user_model()
    
    # Get credentials from environment variables
    username = os.environ.get('uzo')
    email = os.environ.get('udike98@gmail.com')
    password = os.environ.get('Getrichortrydying50')

    # Stop if variables are not set
    if not all([username, email, password]):
        print('Admin credentials not set in environment variables. Skipping superuser setup.')
        return

    try:
        # Try to find the superuser by username
        admin = User.objects.get(username=username)
        
        # Update their details and RESET their password
        admin.email = email
        admin.set_password(password) # This is the key: it hashes the new password
        admin.is_superuser = True
        admin.is_staff = True
        admin.save()
        print(f'Superuser "{username}" already existed, password has been reset.')

    except User.DoesNotExist:
        # If they don't exist, create them
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f'Superuser "{username}" created successfully!')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_create_superuser'), # Make sure this matches your first migration
    ]

    operations = [
        # Make sure this points to the new function name
        migrations.RunPython(set_or_create_superuser),
    ]