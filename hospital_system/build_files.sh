#!/bin/bash
echo "==> Vercel build started..."

# 1. Install dependencies using uv if available, or pip with --break-system-packages
if command -v uv >/dev/null 2>&1; then
    echo "==> Using uv to install dependencies..."
    uv pip install --system -r requirements.txt
else
    echo "==> Using pip to install dependencies..."
    python3 -m pip install -r requirements.txt --break-system-packages || python3 -m pip install -r requirements.txt
fi

# 2. Ensure target static output directories exist
mkdir -p staticfiles_build/static hospital_system/staticfiles_build/static

# 3. Collect static files using Django manage.py
if [ -f "hospital_system/manage.py" ]; then
    echo "==> Running collectstatic in hospital_system..."
    python3 hospital_system/manage.py collectstatic --noinput --clear
    if [ -n "$DATABASE_URL" ]; then
        echo "==> Migrating production database..."
        python3 hospital_system/manage.py migrate --noinput
    fi
elif [ -f "manage.py" ]; then
    echo "==> Running collectstatic..."
    python3 manage.py collectstatic --noinput --clear
    if [ -n "$DATABASE_URL" ]; then
        echo "==> Migrating production database..."
        python3 manage.py migrate --noinput
    fi
fi

# 4. Synchronize staticfiles_build between root and subdirectory
if [ -d "hospital_system/staticfiles_build/static" ]; then
    cp -r hospital_system/staticfiles_build/static/. staticfiles_build/static/ 2>/dev/null || true
fi
if [ -d "staticfiles_build/static" ]; then
    cp -r staticfiles_build/static/. hospital_system/staticfiles_build/static/ 2>/dev/null || true
fi

echo "==> Vercel build complete!"
