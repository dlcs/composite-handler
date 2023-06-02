#!/bin/bash

set -o errexit
set -o pipefail

POSTGRES_USER=$(echo $DATABASE_URL | grep -oP "postgresql://\K(.+?):" | cut -d: -f1)
POSTGRES_PASSWORD=$(echo $DATABASE_URL | grep -oP "postgresql://.*:\K(.+?)@" | cut -d@ -f1)
POSTGRES_HOST=$(echo $DATABASE_URL | grep -oP "postgresql://.*@\K(.+?):" | cut -d: -f1)
POSTGRES_PORT=$(echo $DATABASE_URL | grep -oP "postgresql://.*@.*:\K(\d+)/" | cut -d/ -f1)
POSTGRES_DB=$(echo $DATABASE_URL | grep -oP "postgresql://.*@.*:.*/\K(.+?)$")

# Loop until postgres is ready
postgres_ready() {
python3 << END
import sys

import psycopg2

try:
    psycopg2.connect(
        dbname="${POSTGRES_DB}",
        user="${POSTGRES_USER}",
        password="${POSTGRES_PASSWORD}",
        host="${POSTGRES_HOST}",
        port="${POSTGRES_PORT}",
    )
except psycopg2.OperationalError:
    sys.exit(-1)
sys.exit(0)

END
}
until postgres_ready; do
  >&2 echo 'entrypoint: Waiting for PostgreSQL to become available...'
  sleep 1
done
>&2 echo 'entrypoint: PostgreSQL is available'

if [[ ($MIGRATE) && ("$MIGRATE" = "True") ]]; then
  python manage.py migrate --no-input
  echo "entrypoint: Migrations finished"
  python manage.py createcachetable
  echo "entrypoint: Create cache table finished"
fi

if [[ ($INIT_SUPERUSER) && ("$INIT_SUPERUSER" = "True") ]]; then
  echo "entrypoint: Creating superuser"
  if python3 manage.py createsuperuser --noinput; then
    echo "entrypoint: Created superuser"
  else
    echo "entrypoint: Superuser already exists, unset INIT_SUPERUSER"
  fi
fi
