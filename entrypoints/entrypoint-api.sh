#!/bin/bash

set -o errexit
set -o pipefail

bash entrypoint.sh

echo "collecting static files.."
python manage.py collectstatic --noinput

echo "starting nginx.."
nginx

echo "starting gunicorn on :5000 with $GUNICORN_WORKERS workers"
gunicorn app.wsgi:application --workers $GUNICORN_WORKERS --bind "0.0.0.0:5000"