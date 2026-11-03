#!/usr/bin/env sh
set -e

if [ "$1" = "rundev" ]; then
  sleep 5  # give time for the db to accept connections
  python manage.py runserver_plus 0.0.0.0:8000
  exit 0
fi

if [ "$1" = "runprod" ]; then
  gunicorn config.wsgi -b 0.0.0.0:8000 -k gevent -w 2 --timeout 120 --access-logfile - --error-logfile -
  exit 0
fi

if [ "$1" = "runworker" ]; then
  celery -A config worker -l info
  exit 0
fi

if [ "$1" = "runbeat" ]; then
  celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
  exit 0
fi

if [ "$1" = "migrate" ]; then
  python manage.py migrate
  exit 0
fi

if [ "$1" = "makemigrations" ]; then
  python manage.py makemigrations
  exit 0
fi

exec "$@"
