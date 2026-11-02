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
mkdir -p staticfiles hospital_system/staticfiles

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

# 4. Synchronize staticfiles across root and subdirectory
if [ -d "hospital_system/staticfiles" ]; then
    cp -r hospital_system/staticfiles/. staticfiles/ 2>/dev/null || true
fi
if [ -d "staticfiles" ]; then
    cp -r staticfiles/. hospital_system/staticfiles/ 2>/dev/null || true
fi

# 5. Populate /static nested folder so both /static/ and direct routes resolve
mkdir -p staticfiles/static hospital_system/staticfiles/static
cp -r staticfiles/admin staticfiles/css staticfiles/images staticfiles/js staticfiles/static/ 2>/dev/null || true
cp -r hospital_system/staticfiles/admin hospital_system/staticfiles/css hospital_system/staticfiles/images hospital_system/staticfiles/js hospital_system/staticfiles/static/ 2>/dev/null || true

echo "==> Vercel build complete!"
