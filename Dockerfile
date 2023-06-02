FROM python:3.11
LABEL maintainer="Donald Gray <donald.gray@digirati.com>"
LABEL org.opencontainers.image.source=https://github.com/dlcs/composite-handler

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get --yes install apt-utils && apt-get --yes upgrade \
    && apt-get --yes install poppler-data poppler-utils \
    && apt-get --yes autoremove && apt-get --yes autoclean && apt-get --yes clean \
    && useradd --create-home --home-dir /srv/dlcs --shell /bin/bash --uid 1000 dlcs \
    && python -m pip install --upgrade pip

COPY --chown=dlcs:dlcs ./src/requirements.txt /srv/dlcs
RUN pip install --no-warn-script-location --requirement /srv/dlcs/requirements.txt

COPY --chown=dlcs:dlcs ./src /srv/dlcs
COPY --chown=dlcs:dlcs ./entrypoints /srv/dlcs
RUN chmod +x /srv/dlcs/entrypoint.sh
RUN chmod +x /srv/dlcs/entrypoint-api.sh
RUN chmod +x /srv/dlcs/entrypoint-worker.sh

USER dlcs
WORKDIR /srv/dlcs
