#!/usr/bin/env bash
# Issue Let's Encrypt certs (webroot) while nginx stays up, then enable TLS config.
# Usage: DOMAIN=api.example.com EMAIL=ops@example.com bash scripts/issue_tls.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DOMAIN="${DOMAIN:?Set DOMAIN=api.yourdomain.com}"
EMAIL="${EMAIL:?Set EMAIL=ops@yourdomain.com}"

COMPOSE=(docker compose -f docker-compose.prod.yml --env-file .env.prod)

echo "==> Ensuring HTTP stack is up for ACME challenge"
"${COMPOSE[@]}" up -d nginx

# Compose names volumes as <project>_certbot_www (project ≈ directory name).
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-$(basename "$ROOT")}"
CERTBOT_VOL="${PROJECT_NAME}_certbot_www"

echo "==> Requesting certificate for ${DOMAIN} (webroot via volume ${CERTBOT_VOL})"
docker run --rm \
  -v "${ROOT}/infra/nginx/certs:/etc/letsencrypt" \
  -v "${CERTBOT_VOL}:/var/www/certbot" \
  certbot/certbot certonly \
  --webroot -w /var/www/certbot \
  -d "${DOMAIN}" \
  --email "${EMAIL}" \
  --agree-tos \
  --non-interactive

# Symlink into the path nginx expects (certs dir is both letsencrypt root and nginx mount)
LIVE="live/${DOMAIN}"
if [[ -f "infra/nginx/certs/${LIVE}/fullchain.pem" ]]; then
  ln -sfn "${LIVE}/fullchain.pem" infra/nginx/certs/fullchain.pem
  ln -sfn "${LIVE}/privkey.pem" infra/nginx/certs/privkey.pem
else
  echo "ERROR: expected infra/nginx/certs/${LIVE}/fullchain.pem"
  exit 1
fi

echo "==> Writing TLS compose override and restarting nginx"
cat > docker-compose.tls.override.yml <<'EOF'
services:
  nginx:
    volumes:
      - ./infra/nginx/floodtail.conf:/etc/nginx/conf.d/default.conf:ro
      - ./infra/nginx/certs:/etc/nginx/certs:ro
      - certbot_www:/var/www/certbot:ro
EOF

docker compose \
  -f docker-compose.prod.yml \
  -f docker-compose.tls.override.yml \
  --env-file .env.prod \
  up -d nginx

echo "TLS enabled for https://${DOMAIN}"
echo "Renewal tip: renew via certbot and reload nginx monthly (cron)."
