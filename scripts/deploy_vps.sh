#!/usr/bin/env bash
# Pull latest code and redeploy the Contabo production stack.
# Run from the repo root on the VPS.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env.prod ]]; then
  echo "Missing .env.prod — copy from infra/prod/.env.example and configure secrets."
  exit 1
fi

BRANCH="${1:-main}"

echo "==> Fetching ${BRANCH}"
git fetch origin
git checkout "${BRANCH}"
git pull --ff-only origin "${BRANCH}"

echo "==> Rebuilding API image and restarting stack"
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build --remove-orphans

echo "==> Health check"
sleep 5
curl -fsS http://127.0.0.1/v1/health | head -c 500 || {
  echo
  echo "Health check failed — recent logs:"
  docker compose -f docker-compose.prod.yml --env-file .env.prod logs --tail=80 api
  exit 1
}
echo
echo "Deploy OK"
