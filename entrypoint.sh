#!/bin/sh
set -e

if [ "$1" = "migrate" ]; then
  # The single place where migration files are generated (so that web/bot/celery don't
  # try to do this simultaneously and race against each other).
  python manage.py makemigrations users core --noinput
  python manage.py migrate --noinput
  exit 0
elif [ "$1" = "web" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput || true
  exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60 --access-logfile - --error-logfile -
elif [ "$1" = "bot" ]; then
  python manage.py migrate --noinput
  exec python manage.py runbot
elif [ "$1" = "celery" ]; then
  exec celery -A config worker -l info
elif [ "$1" = "celery-beat" ]; then
  exec celery -A config beat -l info
else
  exec "$@"
fi
