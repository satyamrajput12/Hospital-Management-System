#!/bin/bash
echo "==> Vercel build started..."
python3 -m pip install -r requirements.txt
python3 hospital_system/manage.py collectstatic --noinput --clear
echo "==> Vercel build complete!"
