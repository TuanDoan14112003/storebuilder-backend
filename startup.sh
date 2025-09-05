#!/usr/bin/env sh
set -e
python3 manage.py collectstatic --noinput
# Optional: [ "$RUN_MIGRATIONS" = "1" ] && python3 manage.py migrate --noinput
exec gunicorn storebuilder.wsgi:application \
  --bind 0.0.0.0:${PORT:-8080} \
  --workers ${WEB_CONCURRENCY:-3} \
  --timeout 120 \
  --access-logfile - --error-logfile -
