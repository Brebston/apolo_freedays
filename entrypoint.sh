#!/bin/sh
set -e
case "$1" in
  migrate) python manage.py migrate --noinput ;;
  web)
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput || true
    exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 60 --access-logfile - --error-logfile - ;;
  bot) exec python manage.py runbot ;;
  celery) exec celery -A config worker -l info ;;
  celery-beat) exec celery -A config beat -l info --schedule /tmp/celerybeat-schedule ;;
  celery-all) exec celery -A config worker -B -l info --schedule /tmp/celerybeat-schedule ;;
  *) exec "$@" ;;
esac