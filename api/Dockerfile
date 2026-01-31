FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       libcairo2 \
       libcairo2-dev \
       libpango-1.0-0 \
       libpangocairo-1.0-0 \
       libgdk-pixbuf-2.0-0 \
       libffi-dev \
       shared-mime-info \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install --upgrade wheel==0.46.2 \
    && pip install -r /app/requirements.txt \
    && pip install --upgrade wheel==0.46.2

COPY VERSION /app/VERSION
COPY api/app /app/app
COPY api/alembic /app/alembic
COPY api/alembic.ini /app/alembic.ini

EXPOSE 8000
