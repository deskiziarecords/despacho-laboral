#!/usr/bin/env bash
# ================================================
# Script de despliegue rápido
# Ejecuta en tu máquina LOCAL para subir cambios
# ================================================
set -euo pipefail

# ─── Configuración ─────────────────────────
SERVER="${SERVER:-root@TU_IP}"    # user@host
SSH_KEY="${SSH_KEY:-}"            # ruta a tu key SSH (-i)
BRANCH="${BRANCH:-main}"
APP_DIR="/opt/despacho-laboral"

# ─── Colores ──────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

if [[ "$SERVER" == "root@TU_IP" ]]; then
    warn "Edita este script: pon tu SERVER y SSH_KEY"
    warn "Ejemplo: SERVER=root@123.456.78.90 SSH_KEY=~/.ssh/id_ed25519 ./deploy/deploy.sh"
    exit 1
fi

SSH_CMD="ssh"
if [[ -n "$SSH_KEY" ]]; then
    SSH_CMD="ssh -i $SSH_KEY"
fi

info "Desplegando a $SERVER..."

# 1. Hacer push a GitHub (para que el servidor haga pull)
info "Haciendo push a GitHub..."
git push origin "$BRANCH"

# 2. Conectar al servidor y actualizar
$SSH_CMD "$SERVER" bash -s << EOF
    set -euo pipefail
    cd $APP_DIR

    echo "[✓] Actualizando código..."
    git pull origin $BRANCH

    echo "[✓] Instalando dependencias..."
    source .venv/bin/activate
    uv sync

    echo "[✓] Migraciones..."
    python manage.py migrate --noinput

    echo "[✓] Estáticos..."
    python manage.py collectstatic --noinput --clear

    echo "[✓] Reiniciando Gunicorn..."
    systemctl restart gunicorn

    echo "[✓] Recargando Nginx..."
    nginx -t && systemctl reload nginx

    echo ""
    echo "[✓] ¡Despliegue completado!"
EOF

info "✅ Despliegue exitoso a $SERVER"
