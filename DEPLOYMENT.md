# DEPLOYMENT — Nairobi CAT API (no Streamlit)

Deploy and run the FastAPI backend with Ollama, Keycloak, and Postgres. Next.js (`apps/web`) remains an **empty scaffold** — do not deploy a UI feature set yet.

---

## Local: Docker Compose

Expected services in `docker-compose.yml`:

| Service | Role |
|---------|------|
| `api` | FastAPI (`apps.api.main`) |
| `postgres` | Portfolios, runs, audit (SQLite fallback for API-only local) |
| `keycloak` | JWT issuer; RBAC roles |
| `ollama` | Local instruct models for agents |

```bash
cp .env.example .env
# Set KEYCLOAK_*, OLLAMA_HOST, DATABASE_URL, AES keys, CORS origins
docker compose up --build
```

- API: `http://localhost:8000` · docs: `/docs`  
- Health: `GET /v1/health` (liveness + ollama + model registry)  
- Pull model once: `docker compose exec ollama ollama pull qwen2.5:3b-instruct`

**No Streamlit.** Do not run `streamlit run` or look for `app.py` UI.

---

## Environment (minimum)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres DSN (or SQLite path for local) |
| `OLLAMA_HOST` | e.g. `http://ollama:11434` |
| `OLLAMA_MODEL` | Default `qwen2.5:3b-instruct` |
| `KEYCLOAK_URL` / realm / client | JWT validation |
| `CORS_ORIGINS` | Lockdown; no `*` in prod |
| `AES_KEY` / secrets | PII at rest |
| `ASSUMPTIONS_VERSION` | e.g. `nairobi-pluvial-v1` |

Secrets via env / secret manager only — never commit `.env`.

---

## Ollama notes

- Prefer 1.5B–3B quantized instruct for RAM (Render-friendly).  
- Temperature 0 for structured agents / narratives.  
- If Ollama is down: agents → templates; **runs still complete** (ML + `cat_core`).  
- Models are **not** used for EP / AAL / premium numbers.

---

## Keycloak / Auth

- Compose: Keycloak realm with roles: `admin`, `actuary`, `underwriter`, `client_viewer`, `regulator`, `data_scientist`, `auditor`.  
- Every route JWT-protected except documented health (liveness may be public; readiness can require auth).  
- **Prod:** no anonymous default role.  
- Train endpoints: `data_scientist` / `admin` only.

---

## Render

Suggested layout:

1. **Web service** — FastAPI API  
2. **Private service / sidecar** — Ollama (+ baked or pulled model)  
3. **Managed Postgres**  
4. **Keycloak** — sibling service or external OIDC with same RBAC claims  

```
API  --OLLAMA_HOST-->  Ollama private service
API  --JWT---------->  Keycloak / OIDC
API  --DATABASE_URL->  Postgres
```

Checklist:

- [ ] Secrets in Render env  
- [ ] Healthchecks on API (+ optional Ollama ping from `/v1/health`)  
- [ ] CORS limited to known origins (empty Next.js later)  
- [ ] Disk or object storage for `models/` artifacts (or bake demo versions)  
- [ ] `Nairobi_Data/` available in image or mounted volume  

If RAM is tight: smaller model or template-only agents on Render free tiers.

---

## What not to deploy

- Streamlit (`app.py`, `ui/`) — removed  
- Kenya radial Monte Carlo demo path as product  
- Full Next.js underwriter UI — scaffold only until API contracts freeze  
- Celery / MinIO medallion / LangSmith theatre  

See `IMPLEMENTATION_PLAN.md` and `ROADMAP.md` for phase gates.
