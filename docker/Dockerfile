# NikaNewCrm — образ веб-приложения (контекст сборки: корень репозитория)
FROM python:3.12-slim

WORKDIR /app

# PostgreSQL client major должен совпадать с сервером (PostgreSQL 18).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        | gpg --dearmor -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg \
    && . /etc/os-release \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg] https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list

# Системные зависимости (reportlab, barcode, pycairo/xhtml2pdf)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libcairo2-dev \
    libpq-dev \
    postgresql-client-18 \
    pkg-config \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 nika \
    && useradd --uid 1000 --gid nika --home-dir /app --no-create-home --shell /usr/sbin/nologin nika

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/
COPY oh-oh-icq-sound.mp3 .
COPY wsgi.py .
COPY run.py .
COPY scripts/run_migrations.py ./scripts/

RUN mkdir -p /app/database /app/logs

EXPOSE 5000

ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

COPY docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
