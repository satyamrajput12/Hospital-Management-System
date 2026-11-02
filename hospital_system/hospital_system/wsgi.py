"""
WSGI config for hospital_system project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

# Add hospital_system directory to sys.path so apps can be discovered when run from root
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# On serverless environments (Vercel), ensure /tmp/db.sqlite3 is initialized from db_template.sqlite3
if not os.environ.get('DATABASE_URL'):
    if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or '/var/task' in str(BASE_DIR):
        tmp_db = Path('/tmp/db.sqlite3')
        template_db = BASE_DIR / 'db_template.sqlite3'
        if not tmp_db.exists() and template_db.exists():
            import shutil
            try:
                shutil.copyfile(template_db, tmp_db)
            except Exception:
                pass

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_system.settings')

application = get_wsgi_application()

# Vercel serverless function entrypoint
app = application
