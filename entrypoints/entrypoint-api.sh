#!/bin/bash

set -o errexit
set -o pipefail

bash entrypoint.sh
python manage.py runserver 0.0.0.0:8000