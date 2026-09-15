import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from django.db import connection

print("ENGINE:", settings.DATABASES['default']['ENGINE'])

with connection.cursor() as cursor:
    cursor.execute("SELECT current_database(), current_user;")
    row = cursor.fetchone()
    print("current_database():", row[0])
    print("current_user:", row[1])
