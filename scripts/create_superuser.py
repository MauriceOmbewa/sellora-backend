"""
Convenience script to create a superuser from environment variables.
Usage: python manage.py shell < scripts/create_superuser.py
"""
import os
from apps.accounts.models import User

email = os.environ.get("SUPERUSER_EMAIL", "admin@sellora.com")
name = os.environ.get("SUPERUSER_NAME", "Admin")

if not User.objects.filter(email=email).exists():
    user = User.objects.create_superuser(email=email, name=name, password=None)
    print(f"Superuser created: {email}")
else:
    print(f"Superuser already exists: {email}")
