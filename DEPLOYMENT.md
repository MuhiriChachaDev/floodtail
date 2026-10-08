# FLOODTAIL — Production Deployment Plan

**Targets**

| Layer | Host | Stack |
|-------|------|--------|
| Frontend | **Vercel** | Next.js (`apps/web`) |
| Backend | **Contabo VPS** | FastAPI + Postgres (pgvector) + Ollama + Nginx |

LLMs never invent EP / AAL / premium — those stay in `packages/cat_core` on the VPS.

---

## Architecture

```
Browser
   │
   ▼
Vercel (apps/web)
   │  NEXT_PUBLIC_API_URL=https://api.YOUR_DOMAIN
   │  (browser → API direct; CORS allowlisted)
   ▼
Contabo VPS
   Nginx :80/:443
      │
      ▼
   FastAPI (api:8000) ──► Postgres+pgvector
                     └──► Ollama (agents + embeddings)
```

**Why direct browser→API (not Vercel rewrite):** long CAT runs (30–60s+) time out through Next.js rewrites. `apps/web/lib/api.ts` already calls `NEXT_PUBLIC_API_URL` directly.

---

## Contabo VPS sizing

| Plan | Use |
|------|-----|
| **8 GB RAM / 4 vCPU** | Minimum — API + Postgres + small Ollama (`qwen2.5:3b`) |
| **16 GB RAM / 6+ vCPU** | Recommended — embeddings (`nomic-embed-text`) + ML train/infer headroom |
| Disk | ≥40 GB SSD (images + Ollama weights + models) |

OS: Ubuntu 22.04 or 24.04 LTS. Open ports **22, 80, 443** only. Do not expose Postgres (`5432`) or Ollama (`11434`) publicly.

---

## Phase 0 — Prerequisites

1. Contabo VPS with SSH access and a public IPv4.
2. Domain DNS: `A` record `api.YOUR_DOMAIN` → VPS IP (propagate before TLS).
3. GitHub/Git remote with this repo.
4. Vercel account linked to the same repo.
5. Locally generate secrets (do not reuse `.env.example` defaults):

```bash
# JWT
openssl rand -hex 32

# AES (32 bytes → base64)
python3 -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"

# Postgres password
openssl rand -base64 24
```

---

## Phase 1 — Prepare the repo (already in-tree)

Production-ready artifacts:

| Path | Role |
|------|------|
| `docker-compose.prod.yml` | Contabo stack (api, postgres, ollama, nginx) |
| `infra/docker/api.Dockerfile` | Non-root API image, healthcheck, no `--reload` |
| `infra/nginx/floodtail.http-only.conf` | First-boot HTTP reverse proxy |
| `infra/nginx/floodtail.conf` | HTTP + HTTPS after Certbot |
| `infra/prod/.env.example` | Production env template → `.env.prod` |
| `scripts/bootstrap_vps.sh` | Install Docker, start stack, pull models |
| `scripts/deploy_vps.sh` | Git pull + rebuild |
| `scripts/issue_tls.sh` | Let's Encrypt + switch nginx to TLS |
| `apps/web/vercel.json` | Next.js headers for Vercel |
| `apps/web/.env.example` | `NEXT_PUBLIC_API_URL` |

API changes for prod:

- `CORS_ORIGINS` env allowlist (required; no `*` when `ENV=production`)
- OpenAPI `/docs` off by default in production (`ENABLE_DOCS`)

---

## Phase 2 — Deploy backend on Contabo

### 2.1 Clone and bootstrap

```bash
ssh root@YOUR_VPS_IP
apt-get update && apt-get install -y git
git clone YOUR_REPO_URL /opt/floodtail
cd /opt/floodtail
bash scripts/bootstrap_vps.sh
```

### 2.2 Configure secrets

```bash
nano /opt/floodtail/.env.prod
```

Must set at least:

| Variable | Value |
|----------|--------|
| `POSTGRES_PASSWORD` | Strong random |
| `JWT_SECRET` | Strong random |
| `AES_KEY_BASE64` | 32-byte base64 |
| `CORS_ORIGINS` | `https://YOUR_PROJECT.vercel.app` (+ custom domain if any) |

Then recreate API so env reloads:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d api
```

### 2.3 Seed ML models

Artifacts under `models/` are **gitignored**. Pick one:

**A — Copy from a machine that already trained:**

```bash
# from laptop
scp -r models/ root@YOUR_VPS_IP:/opt/floodtail/models/
```

**B — Train on the VPS via API** (after health is up):

```bash
curl -X POST http://127.0.0.1/v1/models/hazard/train \
  -H 'X-Floodtail-Role: data_scientist' -H 'X-Floodtail-Actor: ops' -H 'X-Floodtail-Tenant: default'
curl -X POST http://127.0.0.1/v1/models/vulnerability/train \
  -H 'X-Floodtail-Role: data_scientist' -H 'X-Floodtail-Actor: ops' -H 'X-Floodtail-Tenant: default'
```

Confirm:

```bash
curl -s http://127.0.0.1/v1/health | python3 -m json.tool
# registry.registry_ready should be true
```

### 2.4 TLS (Let's Encrypt)

```bash
# DNS A record for api.YOUR_DOMAIN must already point here
DOMAIN=api.YOUR_DOMAIN EMAIL=ops@YOUR_DOMAIN bash scripts/issue_tls.sh
```

Verify:

```bash
curl -fsS https://api.YOUR_DOMAIN/v1/health
```

Renewal: Certbot containers + cron, or re-run certbot renew monthly and reload nginx.

### 2.5 Ongoing VPS deploys

```bash
cd /opt/floodtail
bash scripts/deploy_vps.sh main
```

---

## Phase 3 — Deploy frontend on Vercel

### 3.1 Project settings

1. **Add New Project** → import this Git repo.
2. **Root Directory:** `apps/web` (critical for the monorepo).
3. Framework: Next.js (auto-detected).
4. Install / Build: leave defaults (`npm install` / `next build`).

### 3.2 Environment variables (Production + Preview)

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | `https://api.YOUR_DOMAIN` (no trailing slash) |

Preview deployments: either add the same API URL, or add each `*.vercel.app` preview origin to Contabo `CORS_ORIGINS` if you need preview→API.

### 3.3 Deploy

- Push to `main` → Production deploy, **or**
- `cd apps/web && npx vercel --prod` (CLI linked to the project).

### 3.4 CORS lockstep

Whenever the Vercel URL changes, update Contabo:

```bash
# on VPS .env.prod
CORS_ORIGINS=https://floodtail.vercel.app,https://www.YOUR_DOMAIN.com
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d api
```

---

## Phase 4 — Smoke test (E2E)

1. Open the Vercel URL → login / home loads.
2. Browser Network tab: calls go to `https://api.YOUR_DOMAIN/v1/...` with status 200.
3. `GET /v1/health` → `status` ok or degraded only if Ollama still pulling.
4. Create portfolio → start run → metrics (EP / AAL) render.
5. Confirm no CORS errors in the console.

---

## Security checklist

- [ ] `.env.prod` never committed; defaults from `.env.example` replaced
- [ ] `ENV=production`, `ENABLE_DOCS=false`
- [ ] `CORS_ORIGINS` exact Vercel (+ custom) origins only
- [ ] UFW: 22/80/443 only; Postgres & Ollama not published
- [ ] TLS on `api.YOUR_DOMAIN`
- [ ] SSH key auth; disable password root login when stable
- [ ] Contabo snapshots / backups enabled
- [ ] Model volume `./models` backed up after train

---

## Local development (unchanged)

```bash
cp .env.example .env
docker compose up --build          # api + postgres + ollama + keycloak + web
# or
uvicorn apps.api.main:app --reload --port 8000
cd apps/web && npm run dev
```

Dev compose still uses `--reload` and published ports. Production uses `docker-compose.prod.yml` only.

---

## Troubleshooting

<<<<<<< HEAD
| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres DSN (or SQLite path for local) |
| `OLLAMA_HOST` | e.g. `http://ollama:11434` |
| `OLLAMA_MODEL` | Default `qwen2.5:3b-instruct` |
| `KEYCLOAK_URL` / realm / client | JWT validation |
| `CORS_ORIGINS` | Lockdown; no `*` in prod |
| `AES_KEY` / secrets | PII at rest |
| `ASSUMPTIONS_VERSION` | e.g. `nairobi-pluvial-v1` |

<<<<<<< HEAD
```bash
streamlit run app.py
```
- The browser will automatically open to `http://localhost:8501`.
- In the sidebar, click **🎯 Demo** to immediately execute and load the frozen 10,000-year demonstration pipeline.

### B. Headless CLI Bootstrap & Smoke Test
To verify database, configuration, and environment integrity headlessly:

```bash
python app.py
```
Output:
```
FLOODTAIL backend bootstrap complete. Run ID: <UUID>
```

### C. Automated Test Suite Execution
Execute the entire regression and validation suite:

```bash
pytest -v
```
All 141 tests across foundation, data layer, catastrophe engine, risk analytics, agent workflow, uncertainty, skeptic red-teaming, grounding, shadow exposure, treaty XOL, and frontend smoke will execute and pass.
=======
Secrets via env / secret manager only — never commit `.env`.
>>>>>>> c3d0325909f5ce2a26452beab68b6bc838e8167d
=======
| Symptom | Fix |
|---------|-----|
| CORS error in browser | Add exact Vercel origin to `CORS_ORIGINS`; recreate `api` |
| `registry_ready: false` | Seed/train models into `./models` on the VPS |
| Ollama timeouts / degraded health | Wait for `ollama pull`; upgrade RAM; agents fall back to templates |
| 413 on upload | Nginx `client_max_body_size 55m` already set; check `MAX_UPLOAD_MB` |
| Nginx fails on TLS conf | Stay on `floodtail.http-only.conf` until certs exist |
| Vercel build can't find app | Set Root Directory to `apps/web` |
| Long run fails via `/backend/*` rewrite | Expected — use direct `NEXT_PUBLIC_API_URL` (already default in `lib/api.ts`) |
>>>>>>> 70097cdd3a2f1c7d590814eb570d33796d7486e9

---

## What not to deploy on Vercel

- FastAPI, Postgres, Ollama, Keycloak, ML training — VPS only  
- Streamlit (removed)  
- Secrets in frontend env beyond `NEXT_PUBLIC_*` (anything `NEXT_PUBLIC_` is visible to browsers)

---

## Rollback

**Vercel:** Promote previous deployment in the dashboard.  
**VPS:**

```bash
cd /opt/floodtail
git log -5 --oneline
git checkout PREVIOUS_SHA
bash scripts/deploy_vps.sh HEAD   # or: docker compose ... up -d --build
```

---

## Order of operations (summary)

1. Contabo: bootstrap → `.env.prod` secrets → seed models → DNS → TLS  
2. Set `CORS_ORIGINS` to the intended Vercel URL (can update after first Vercel deploy)  
3. Vercel: Root Directory `apps/web` → `NEXT_PUBLIC_API_URL` → deploy  
4. Smoke test E2E → lock CORS → enable Contabo backups  

See also: `README.md`, `AGENTS.md`, `RISK_GOVERNANCE.md`.
