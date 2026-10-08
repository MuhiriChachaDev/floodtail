# FLOODTAIL — Nairobi Urban Flood CAT (Team A)

Reinsurance-oriented **Nairobi County pluvial flood** catastrophe prototype for the Team A Urban Flood Challenge.

<<<<<<< HEAD
**Release**: `FLOODTAIL Grade 1 Commercial Release v1.0.0`  
**Test Suite**: 141 / 141 Passed (100% Deterministic Actuarial Green)  
**Supported Runtimes**: Python 3.10 – 3.14 (Verified on Python 3.14.5)  
**Primary Currency Base**: Kenya Shillings (KES) with multi-currency normalizer (USD, EUR, GBP)  
=======
**Pipeline:** Hazard → Vulnerability → Exposure → Financial engine → EP / return-period curve

**AI posture (option 3):** trained predictive ML (hazard + vulnerability) **and** agentic AI (Ollama) around a **deterministic financial / EP core**. LLMs never invent loss, EP, AAL, or premium numbers.
>>>>>>> c3d0325909f5ce2a26452beab68b6bc838e8167d

---

## What this is

| In scope | Out of scope |
|----------|----------------|
| Nairobi County pluvial (surface-water) flood | Treaty structuring |
| Synthetic 600-building exposure + proxy GeoTIFFs | Real client portfolios |
| Trained hazard & vulnerability models | Multi-peril |
| Agentic ingest / briefing / Q&A (Ollama) | Full hydrology |
| Deterministic loss, EP, AAL, accumulation | Kenya-wide Monte Carlo catalogue |
| kenyaRE-hard security (Keycloak, RBAC, audit) | Streamlit UI |

Streamlit has been **removed**. The product surface for the hackathon is the **FastAPI** backend; `apps/web` is an **empty Next.js scaffold** (no UI features yet).

---

## Data (`Nairobi_Data/`)

| Asset | Role |
|-------|------|
| `exposure_nairobi_with_hazard.csv` | 600 synthetic buildings + 5-tier hazard scores (recommended start) |
| `exposure_nairobi_synthetic.csv` | Same locations without scores (raster / enrichment path) |
| `nairobi_pluvial_proxy_{common,occasional,moderate,severe,extreme}.tif` | Proxy susceptibility rasters (0–1) |
| `nairobi_hotspots_geocoded.csv` | 24 government-named hotspots (proxy QA ≈ 12/24) |

All exposure rows are labelled `synthetic=True`. Proxy hazard is **not** gauge-validated flood depth.

---

## Stack

```
apps/web     Next.js — empty scaffold only
apps/api     FastAPI — JWT/Keycloak, RBAC, /v1/*
packages/
  agents/    Agentic AI (Ollama / LangGraph-style) + RAG/memory tools
  ml/        HazardModel + VulnerabilityModel (train + infer)
  cat_core/  Deterministic depth, loss, EP, accumulation, pricing
  rag/       PDF/DOCX ingest → chunk → embed → pgvector retrieve
  memory/    LangChain long-term memory (Postgres / in-memory)
  security/  RBAC, prompt defence, AES, tenant, audit chain
  xai/       SHAP, counterfactuals, validated narratives
  llm/       Ollama client
```

Infra: Docker Compose (`api` + `postgres` (pgvector) + `keycloak` + `ollama`). Deploy target: Render (API + Ollama).

**RAG / memory:** `POST /v1/knowledge/documents` ingests PDF/DOCX/text; agents retrieve via tools. Long-term memory: `/v1/memory/*`. Both prefer Postgres+pgvector; fall back to in-memory when Postgres is down. LLMs still never invent EP/AAL/premium — those stay in `cat_core`.

---

## How to run (API)

```bash
# From repo root — after Phase 0 scaffold exists
cp .env.example .env
docker compose up --build

# Or local API (Postgres/Ollama optional; see DEPLOYMENT.md)
uvicorn apps.api.main:app --reload --port 8000
```

Health: `GET /v1/health`  
OpenAPI: `http://localhost:8000/docs`

Typical flow:

1. `POST /v1/portfolios` — upload CSV or select built-in Nairobi set  
2. `POST /v1/models/hazard/train` / `vulnerability/train` — register pinned models  
3. `POST /v1/runs` — run pipeline  
4. `GET /v1/runs/{id}/metrics` — AAL, EP points, tier losses (`data_labels` on every payload)  
5. `GET /v1/runs/{id}/narrative` — validated Ollama briefing (numbers from allowlist only)

There are **no Streamlit launch instructions**. Frontend UI is deferred.

---

## Docs map

<<<<<<< HEAD
Run all 141 tests:
```bash
pytest -v
```

```
======================= 141 passed in 117.62s (0:01:57) =======================
```

| Test File | Tests | Coverage |
|:---|:---:|:---|
| `tests/test_foundation.py` | 30 | Pydantic schemas, data contracts, config, bootstrap smoke |
| `tests/test_data_layer.py` | 27 | SQLite CRUD, schema mapper, normalizer, quality auditor |
| `tests/test_catastrophe_engine.py`| 22 | Poisson simulator, hazard intersection, vulnerability, ELT/YLT |
| `tests/test_risk_analytics.py` | 18 | AAL, OEP/AEP, VaR/TVaR, Euler allocation, pricing waterfall, CRN |
| `tests/test_agent_workflow.py` | 20 | 11-agent sequential orchestrator, governance, trace validation |
| `tests/test_frontend_smoke.py` | 11 | UI components, 16-page catalogue, Plotly charts, audit verification |
| `tests/test_uncertainty.py` | 4 | YLT bootstrap uncertainty corridors (AAL, TVaR, Premium) |
| `tests/test_skeptic.py` | 2 | Adversarial red-team stress testing & assumption sensitivity |
| `tests/test_grounding.py` | 2 | Numeric Grounding Guard & AI hallucination prevention |
| `tests/test_shadow_exposure.py` | 2 | Protection gap & regional density multiplier modeling |
| `tests/test_treaty.py` | 3 | Reinsurance treaty layering (Cedant retention & Cat XOL layers) |
=======
| Doc | Purpose |
|-----|---------|
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Locked architecture, phases, API contract |
| [ROADMAP.md](ROADMAP.md) | **Full E2E completion roadmap** (phases, checklists, 3-day plan) |
| [ASSUMPTIONS.md](ASSUMPTIONS.md) | Assumptions register (status taxonomy) |
| [METHODOLOGY.md](METHODOLOGY.md) | CAT + ML + agents + financial methodology |
| [EXPLAINABILITY.md](EXPLAINABILITY.md) | SHAP, counterfactuals, narrative validation |
| [MODEL_CARD.md](MODEL_CARD.md) | Nairobi prototype model card |
| [AGENTS.md](AGENTS.md) | Agentic + ML + deterministic stage list |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Compose, Ollama, Keycloak, Render |
| [RISK_GOVERNANCE.md](RISK_GOVERNANCE.md) | Human-in-loop, RBAC, audit |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | Judge demo against API/metrics |
| [FINAL_VALIDATION_REPORT.md](FINAL_VALIDATION_REPORT.md) | Superseded; pending re-validation |
| [Team_A_Nairobi_Problem_Statement.docx](Team_A_Nairobi_Problem_Statement.docx) | Hackathon problem authority |
>>>>>>> c3d0325909f5ce2a26452beab68b6bc838e8167d

---

## Hackathon deliverables

1. Working E2E demo via API  
2. EP / return-period curve  
3. AI that materially changes output (trained ML and/or free-text exposure agent)  
4. Assumptions labelled in payloads and docs  
5. Results interface — **API contracts now; Next.js UI later**  
6. Written note: sources / assumptions / AI role (this README + ASSUMPTIONS + METHODOLOGY + MODEL_CARD)

**Honest labelling:** synthetic exposure, proxy rasters, prototype RP map, synthetic ML labels — never claimed as real Nairobi flood gauges or underwriting-grade portfolios.
