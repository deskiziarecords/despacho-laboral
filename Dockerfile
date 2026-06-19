# ================================================
# Dockerfile para Despacho Laboral
# Compatible con DigitalOcean App Platform
# Incluye: WeasyPrint (PDFs) + Playwright (Chromium)
# ================================================

# --- Build Stage ---
FROM python:3.13-slim-bookworm AS builder

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Instalar dependencias del sistema para compilar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Runtime Stage ---
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Instalar dependencias del sistema para:
#   - WeasyPrint (Pango, Cairo, GDK-PixBuf, libffi)
#   - Playwright (Chromium browser)
#   - PostgreSQL (libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    shared-mime-info \
    # Playwright / Chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0tty \
    libatk-bridge2.0-0tty \
    libcups2tty \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2tty \
    libpango-1.0-0 \
    libcairo2 \
    # PostgreSQL
    libpq5 \
    # Utils
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias de Python desde builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Instalar Chromium para Playwright
RUN playwright install chromium

# Copiar código de la aplicación
COPY . .

# Recolectar archivos estáticos
RUN python manage.py collectstatic --noinput --clear

# Puerto que usa DO App Platform (8080)
EXPOSE 8080

# Comando de inicio: Gunicorn
# Entrypoint: migraciones + servidor
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8080 --workers 3 --timeout 120"]
