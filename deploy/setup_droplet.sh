#!/usr/bin/env bash
# ================================================
# Script de aprovisionamiento para DigitalOcean Droplet
# SO: Ubuntu 22.04 LTS / 24.04 LTS
# ================================================
set -euo pipefail

# ─── Colores ──────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ─── Validar ejecución como root ────────────
if [[ $EUID -ne 0 ]]; then
    err "Este script debe ejecutarse como root (sudo)."
fi

# ─── Variables (edita según tu proyecto) ───
REPO_URL="${REPO_URL:-https://github.com/TU_USUARIO/despacho-laboral.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="/opt/despacho-laboral"
DOMAIN="${DOMAIN:-}"  # ej: despacho.midominio.com — dejar vacío si solo IP
APP_USER="www-data"
PYTHON_VERSION="3.13"

info "=========================================="
info "Aprovisionando servidor para Despacho Laboral"
info "Repo: $REPO_URL [$BRANCH]"
info "Destino: $APP_DIR"
info "=========================================="
echo ""

# ─── 1. Actualizar sistema ────────────────
info "Actualizando paquetes del sistema..."
apt-get update -y && apt-get upgrade -y

# ─── 2. Dependencias del sistema ──────────
info "Instalando dependencias del sistema..."
apt-get install -y \
    curl wget git build-essential \
    python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx \
    # WeasyPrint: librerías para renderizar PDF
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 shared-mime-info \
    # Playwright / Chromium
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2

# ─── 3. Instalar uv (gestor de paquetes) ──
if ! command -v uv &>/dev/null; then
    info "Instalando uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.cargo/env" 2>/dev/null || true
    export PATH="$HOME/.cargo/env:$HOME/.local/bin:$PATH"
fi
info "uv $(uv --version 2>/dev/null || echo 'instalado')"

# ─── 4. Clonar repositorio ─────────────────
if [[ -d "$APP_DIR" ]]; then
    warn "El directorio $APP_DIR ya existe. Actualizando..."
    cd "$APP_DIR" && git pull origin "$BRANCH"
else
    info "Clonando repositorio..."
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

# ─── 5. Crear entorno virtual e instalar deps ──
info "Creando entorno virtual con uv..."
uv venv --python "$PYTHON_VERSION" .venv
source .venv/bin/activate

info "Instalando dependencias de Python..."
uv sync

info "Instalando dependencias de Playwright..."
uv run playwright install chromium

# ─── 6. Configurar PostgreSQL ──────────────
info "Configurando PostgreSQL..."
DB_NAME="despacho_laboral"
DB_USER="despacho_user"
DB_PASS="$(openssl rand -base64 24)"

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    info "Base de datos '$DB_NAME' creada."
else
    warn "El usuario '$DB_USER' ya existe. Se reutilizará."
fi

# ─── 7. Crear archivo .env ────────────────
if [[ ! -f "$APP_DIR/.env" ]]; then
    info "Creando archivo .env..."
    SECRET_KEY=$(uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    cat > "$APP_DIR/.env" <<EOF
SECRET_KEY=$SECRET_KEY
DEBUG=false
ALLOWED_HOSTS=$DOMAIN,$(curl -s ifconfig.me 2>/dev/null || echo "localhost")
CSRF_TRUSTED_ORIGINS=https://$DOMAIN
DATABASE_URL=postgres://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EOF
    info ".env creado."
else
    warn "El archivo .env ya existe. No se sobrescribió."
fi

# ─── 8. Migraciones, estáticos, superusuario ──
cd "$APP_DIR"
info "Ejecutando migraciones..."
uv run python manage.py migrate --noinput

info "Recolectando archivos estáticos..."
uv run python manage.py collectstatic --noinput --clear

info "Creando superusuario por defecto..."
uv run python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@despacho.com', 'Admin123!')
    print('Superusuario creado: admin / Admin123!')
else:
    print('Superusuario admin ya existe.')
"

# ─── 9. Configurar Gunicorn como servicio ──
info "Configurando Gunicorn..."
mkdir -p /var/log/gunicorn
chown $APP_USER:$APP_USER /var/log/gunicorn

cp "$APP_DIR/deploy/gunicorn.service" /etc/systemd/system/gunicorn.service
systemctl daemon-reload
systemctl enable gunicorn
systemctl start gunicorn
info "Gunicorn iniciado."

# ─── 10. Configurar Nginx ─────────────────
if [[ -n "$DOMAIN" ]]; then
    info "Configurando Nginx para dominio $DOMAIN..."
    sed "s/despacho.midominio.com/$DOMAIN/g" "$APP_DIR/deploy/nginx.conf" > /etc/nginx/sites-available/despacho-laboral
else
    IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    warn "Sin dominio configurado. Usando IP: $IP"
    sed "s/despacho.midominio.com/$IP/g" "$APP_DIR/deploy/nginx.conf" > /etc/nginx/sites-available/despacho-laboral
    # Deshabilitar redirect HTTPS si no hay dominio
    sed -i 's/return 301/# return 301/' /etc/nginx/sites-available/despacho-laboral
    sed -i 's/listen 443 ssl;/listen 80;/g' /etc/nginx/sites-available/despacho-laboral
    sed -i '/ssl_certificate/d' /etc/nginx/sites-available/despacho-laboral
    sed -i '/ssl_certificate_key/d' /etc/nginx/sites-available/despacho-laboral
    sed -i '/ssl_dhparam/d' /etc/nginx/sites-available/despacho-laboral
    sed -i '/include \/etc\/letsencrypt/d' /etc/nginx/sites-available/despacho-laboral
fi

ln -sf /etc/nginx/sites-available/despacho-laboral /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

info "Verificando configuración de Nginx..."
nginx -t || err "Error en configuración de Nginx"

systemctl enable nginx
systemctl restart nginx
info "Nginx configurado."

# ─── 11. Configurar SSL con Certbot ──────
if [[ -n "$DOMAIN" ]] && command -v certbot &>/dev/null; then
    info "Configurando SSL con Certbot..."
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "admin@$DOMAIN" || \
    warn "Certbot falló. Puedes configurar SSL manualmente con: sudo certbot --nginx -d $DOMAIN"
fi

# ─── 12. Configurar cron para recordatorios ──
info "Configurando cron para recordatorios automáticos..."
(crontab -l 2>/dev/null; echo "0 8 * * 1-5 cd $APP_DIR && .venv/bin/python manage.py enviar_recordatorios --days=3 >> /var/log/despacho-recordatorios.log 2>&1") | crontab -
info "Cron configurado: recordatorios diarios a las 8 AM (lun-vie)."

# ─── 13. Ajustar permisos ─────────────────
info "Ajustando permisos..."
chown -R $APP_USER:$APP_USER "$APP_DIR"
chown -R $APP_USER:$APP_USER /var/log/gunicorn
chmod 750 "$APP_DIR"

# ─── 14. Limpiar ──────────────────────────
info "Limpiando..."
apt-get autoremove -y

# ─── Resumen ──────────────────────────────
echo ""
info "=========================================="
info "  ✅  Servidor aprovisionado con éxito!"
info "=========================================="
echo ""
echo "  URL:        http://${DOMAIN:-$(curl -s ifconfig.me 2>/dev/null)}"
echo "  Usuario:    admin"
echo "  Password:   Admin123!"
echo "  DB:         $DB_NAME (user: $DB_USER)"
echo ""
echo "  📁 App:     $APP_DIR"
echo "  🗄️  DB:     PostgreSQL local"
echo "  🌐 Nginx:   Activo"
echo "  ⚙️  Gunicorn: Activo"
echo "  ⏰ Cron:    Recordatorios 8 AM lun-vie"
echo ""
if [[ -z "$DOMAIN" ]]; then
    warn "  ⚠️  Sin dominio. Accede por IP."
    warn "  Para SSL, configura un dominio y ejecuta:"
    warn "    sudo certbot --nginx -d tudominio.com"
fi
echo ""
info "¡IMPORTANTE! Cambia la contraseña del superusuario"
info "y la del usuario de PostgreSQL en $APP_DIR/.env"
echo ""
