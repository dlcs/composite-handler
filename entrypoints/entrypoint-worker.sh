#!/bin/bash

set -o errexit
set -o pipefail

bash entrypoint.sh

if [[ -n "$PRIORITY_QUEUE_NAME" ]]; then
  python manage.py qcluster &
  Q_CLUSTER_NAME="$PRIORITY_QUEUE_NAME" python manage.py qcluster &
  # If either cluster dies, exit so the container is restarted with both.
  wait -n
  exit 1
else
  python manage.py qcluster
fi
