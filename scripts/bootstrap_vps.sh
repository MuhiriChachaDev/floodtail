#!/usr/bin/env bash
# Bootstrap FLOODTAIL on a Contabo VPS (Ubuntu 22.04/24.04).
# Run as root or with sudo from the cloned repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Installing Docker Engine + Compose plugin"
if ! command -v docker >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

echo "==> Opening firewall ports 22, 80, 443 (ufw)"
if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw --force enable || true
fi

if [[ ! -f .env.prod ]]; then
  echo "==> Creating .env.prod from template — EDIT SECRETS BEFORE GOING LIVE"
  cp infra/prod/.env.example .env.prod
fi

mkdir -p models infra/nginx/certs

echo "==> Building and starting production stack"
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

echo "==> Pulling Ollama models (may take several minutes)"
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T ollama \
  ollama pull qwen2.5:3b-instruct || true
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T ollama \
  ollama pull nomic-embed-text || true

echo "==> Waiting for API health"
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1/v1/health >/dev/null 2>&1; then
    echo "API is up"
    curl -fsS http://127.0.0.1/v1/health | head -c 400 || true
    echo
    break
  fi
  sleep 3
  if [[ "$i" -eq 30 ]]; then
    echo "WARN: API health not ready yet — check: docker compose -f docker-compose.prod.yml logs api"
  fi
done

echo
echo "Next steps:"
echo "  1. Edit .env.prod (CORS_ORIGINS, POSTGRES_PASSWORD, JWT_SECRET, AES_KEY_BASE64)"
echo "  2. Seed models: scp -r models/ user@vps:/path/to/floodtail/models/"
echo "     or train via API: POST /v1/models/hazard/train + vulnerability/train"
echo "  3. Point DNS A record for api.YOUR_DOMAIN to this VPS"
echo "  4. Issue TLS: see DEPLOYMENT.md Certbot section"
echo "  5. Set Vercel NEXT_PUBLIC_API_URL=https://api.YOUR_DOMAIN"
