#!/bin/bash

set -o errexit
set -o pipefail

bash entrypoint.sh
python manage.py qcluster