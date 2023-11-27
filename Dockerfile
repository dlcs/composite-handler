FROM python:3.12
LABEL maintainer="Donald Gray <donald.gray@digirati.com>"
LABEL org.opencontainers.image.source=https://github.com/dlcs/composite-handler

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV GUNICORN_WORKERS=2
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get --yes install apt-utils && apt-get --yes upgrade \
    && apt-get install -y nginx \
    && apt-get --yes install poppler-data poppler-utils \
    && apt-get --yes autoremove && apt-get --yes autoclean && apt-get --yes clean \
    && useradd --create-home --home-dir /srv/dlcs --shell /bin/bash --uid 1000 dlcs \
    && python -m pip install --upgrade pip

# Copy nginx config and create appropriate folders
COPY --chown=dlcs:dlcs ./nginx.conf /etc/nginx/nginx.conf
RUN mkdir -p /var/cache/nginx && chown -R dlcs:dlcs /var/cache/nginx && \
    mkdir -p /var/log/nginx  && chown -R dlcs:dlcs /var/log/nginx && \
    mkdir -p /var/lib/nginx  && chown -R dlcs:dlcs /var/lib/nginx && \
    touch /run/nginx.pid && chown -R dlcs:dlcs /run/nginx.pid && \
    chown -R dlcs:dlcs /etc/nginx && \
    chmod -R 777 /etc/nginx/conf.d

RUN mkdir /srv/dlcs/app_static && chown dlcs:dlcs /srv/dlcs/app_static/

COPY --chown=dlcs:dlcs ./src/requirements.txt /srv/dlcs
RUN pip install --no-warn-script-location --requirement /srv/dlcs/requirements.txt

COPY --chown=dlcs:dlcs ./src /srv/dlcs
COPY --chown=dlcs:dlcs ./entrypoints /srv/dlcs

RUN chmod +x /srv/dlcs/entrypoint.sh
RUN chmod +x /srv/dlcs/entrypoint-api.sh
RUN chmod +x /srv/dlcs/entrypoint-worker.sh

USER dlcs
WORKDIR /srv/dlcs
