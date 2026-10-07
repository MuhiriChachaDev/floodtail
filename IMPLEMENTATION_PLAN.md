# FLOODTAIL → Nairobi Urban Flood CAT — Implementation Plan

**Status:** Plan only (no implementation until approved)  
**Target:** Nairobi County pluvial flood catastrophe model for a reinsurance underwriting workflow  
**Stack:** FastAPI backend + empty Next.js scaffold + Ollama (local/small models) + kenyaRE-hard security  
**Principle:** **Both** predictive ML **and** agentic AI around a **deterministic financial / EP core**; lean file count; end-to-end.

**AI posture (locked — option 3):**

1. **Train ML models for prediction** — hazard susceptibility and vulnerability/damage-ratio models are trained, versioned, and used at inference (not heuristics-only).
2. **Agentic AI** — LLM agents (Ollama, LangGraph-style graph) orchestrate ingestion, enrichment, free-text exposure, briefing, Q&A, and human-gate messaging.
3. **Deterministic / statistical core** — ground-up loss, EP curve, AAL, accumulation, pricing, audit math **never** come from an LLM.

---

## 1. Problem we are solving

Team A (Nairobi Urban Flood Challenge) requires an end-to-end CAT pipeline:

**Hazard → Vulnerability → Exposure → Financial engine → EP / return-period curve**

for Nairobi pluvial (surface-water) flooding, using open/synthetic data, with:

- Honest labelling of synthetic vs real / assumed vs measured
- AI that **materially changes** model output (via trained ML predictions and/or agent-built exposure)
- An interface an underwriter can understand (frontend deferred; API contracts first)
- Reinsurance-useful outputs: portfolio loss by return period, accumulation, explainability, auditable decisions

Primary data already in-repo: `Nairobi_Data/`.

| Asset | Role |
|-------|------|
| `exposure_nairobi_with_hazard.csv` | 600 synthetic buildings + 5-tier hazard scores (recommended start) |
| `exposure_nairobi_synthetic.csv` | Same locations without scores (for raster lookup / AI enrichment path) |
| `nairobi_pluvial_proxy_*.tif` | 5 severity-tier susceptibility rasters (0–1) |
| `nairobi_hotspots_geocoded.csv` | 24 government-named hotspots (proxy validates ~12/24) |

Optional enrichment: OSM drainage/waterways, satellite-derived imperviousness / depression proxies — only where they improve features and are cited.

---

## 2. Decisions locked (from product owner)

| # | Decision |
|---|----------|
| 1 | **Nairobi County only** — `Nairobi_Data` + OSM/satellite if needed |
| 2 | **Both predictive ML + agentic AI**; financial/EP/accumulation remain deterministic/statistical |
| 3 | **Kill Streamlit** — scaffold Next.js frontend, **add no UI features yet** |
| 4 | **Hard security** — kenyaRE-style (not demo-lite) |
| 5 | **Ollama local** — small models (Qwen / DeepSeek-class); ship with backend (Render/Docker) |
| 6 | **Plan first** — this document; code after approval |
| 7 | **Option 3** — train ML for predictions **and** use agentic AI |

---

## 3. Architecture (lean end-to-end)

```
┌─────────────────────────────────────────────────────────────────┐
│  apps/web  (Next.js)     EMPTY scaffold only — no pages/features │
└─────────────────────────────────────────────────────────────────┘
                              │ (future)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  apps/api  (FastAPI)                                              │
│  JWT/Keycloak · RBAC · tenant · rate limit · audit hooks          │
│  /v1/portfolios · /v1/runs · /v1/results · /v1/xai · /v1/query    │
│  /v1/models · /v1/audit · /v1/health                              │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│ packages/agents  (AGENTIC AI — Ollama / LangGraph-style)          │
│ SchemaValidate · PII · Geocode · Enrich · FreeTextExposure        │
│ Briefing · Query · HumanGate messaging                            │
│ Every LLM call: prompt defence + output number validation         │
└─────────────────────────────────────────────────────────────────┘
          │ features / structured exposure / narratives
          ▼
┌─────────────────────────────────────────────────────────────────┐
│ packages/ml  (PREDICTIVE ML — train + infer)                      │
│ HazardModel (train/predict) · VulnerabilityModel (train/predict)  │
│ Model registry (joblib + SHA-256) · SHAP for tree models          │
└─────────────────────────────────────────────────────────────────┘
          │ predicted hazard scores / damage ratios
          ▼
┌─────────────────────────────────────────────────────────────────┐
│ packages/cat_core  (DETERMINISTIC / STATISTICAL — no LLM)         │
│ score→depth · financial loss · EP/AAL · accumulation · pricing    │
│ risk appetite rules · audit math                                  │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│ packages/security + packages/xai                                  │
│ RBAC, AES, prompt defence, output validation, hash audit, tenant  │
│ SHAP + counterfactuals + validated narratives + model cards       │
└─────────────────────────────────────────────────────────────────┘

Data: Nairobi_Data/ · model artifacts · Postgres · audit chain
Infra: Docker Compose (api + ollama + postgres + keycloak)
Deploy: Render (API + Ollama sidecar / private service)
```

**Hard boundary:** LLM agents may change **inputs** (exposure rows, enrichment, briefings). ML models may change **predicted hazard/damage**. Only `cat_core` may emit **loss, EP, AAL, premium** numbers.

**Explicit non-goals for v1:** treaty structuring, real client portfolios, multi-peril, full hydrology, Streamlit, fleshed-out Next.js UI, Celery/MinIO bronze–silver–gold theatre, LangSmith. Training is **explicit + versioned** (CLI/API job), not silent retrain on every UI click.

---

## 4. Modelling design (Nairobi CAT)

### 4.0 Separation of concerns (option 3)

| Layer | What it does | Train? | LLM? |
|-------|--------------|--------|------|
| **Agentic AI** | Ingest, PII, geocode, enrich, free-text→exposure, briefings, Q&A, gate prompts | No | **Yes (Ollama)** |
| **Predictive ML** | Predict hazard scores & damage ratios from features | **Yes** | No |
| **cat_core** | depth mapping, GU loss, EP/AAL, accumulation, pricing, appetite | No | No |

### 4.1 Hazard — features + trained ML prediction

**Feature inputs (deterministic / geo):**

1. Starter scores from `exposure_nairobi_with_hazard.csv` and/or GeoTIFF sample via `rasterio`.
2. Enrichment (agent + geo): distance to OSM waterways, distance to 24 hotspots, optional DEM/depression flags.
3. Map predicted susceptibility → depth:

   ```
   depth_m(tier, loc) = hazard_score_pred(tier, loc) × D_max
   ```

   Default `D_max = 4.0 m` (documented).

4. Return-period map (documented prototypes):

   | Tier | Assumed RP (years) | Approx. AEP |
   |------|--------------------|-------------|
   | common | 5 | 0.20 |
   | occasional | 20 | 0.05 |
   | moderate | 50 | 0.02 |
   | severe | 100 | 0.01 |
   | extreme | 250 | 0.004 |

5. Hotspot QA: report known proxy miss (drainage-driven areas).

**Predictive ML (trains and predicts):**

- **`HazardModel`**: gradient-boosted tree (XGBoost or LightGBM) predicting per-tier susceptibility.
- **Training labels (honest, synthetic):** proxy raster/CSV scores + hotspot-positive uplift for the 24 named locations + mild uplift near OSM drainage where proxy is cold. Document as synthetic labelling — never claim real flood gauges.
- **Train job** (CLI/`POST /v1/models/hazard/train`) → artifacts in `models/hazard/{version}/` with SHA-256 registry.
- **Inference at run time** loads pinned version; run stores `hazard_model_version` and baseline-vs-predicted delta for XAI.
- No LLM inside hazard numeric prediction.

### 4.2 Vulnerability — JRC prior + trained ML prediction

Housing classes: `informal_iron_sheet`, `semi_permanent`, `permanent_masonry`, `concrete_rcc`.

- **Prior:** JRC/Huizinga-adapted depth–damage curves (ASSUMPTIONS.md).
- **`VulnerabilityModel`:** regressor trained on synthetic labels from the prior (± noise / class modifiers); optional residual vs prior.
- Inference: `damage_ratio = clip(model.predict(depth, housing_class, …))`.
- SHAP on tree model for local damage drivers.
- Agentic optional: LLM proposes curve research notes → **human-approved** parameter patch only.

### 4.3 Exposure + agentic ingestion

- CSV loader for Nairobi schema; always stamp `synthetic=True`.
- DQ: Nairobi bbox, TIV > 0, valid housing class, coords.
- **Agentic path:** free-text → Ollama agent → structured rows → schema validation → financial engine (materially changes portfolio).
- PII detect/hash agent before persist.

### 4.4 Financial engine + EP curve (deterministic / statistical only)

- `loss = damage_ratio_pred × tiv_kes` (ratios from ML; multiply is deterministic)
- Aggregate by tier → EP curve; AAL from discrete RPs
- Optional light MC for uncertainty bands — not a 10k-year Kenya catalogue
- **LLM never emits these numbers**

### 4.5 Reinsurance decision layer (slim)

- Hotspot / class accumulation, optional technical premium, deterministic appetite rules
- Evidence package + mandatory human justification → hash-chained audit

### 4.6 Pipeline: agentic graph + ML + deterministic core

| Stage | Type | Critical? |
|-------|------|-----------|
| 1 SchemaValidate / PII / Geocode / Enrich | Agentic + rules | Yes |
| 2 FreeTextExposure (optional) | **Agentic LLM** | No |
| 3 HumanGate_1 (approve features) | Human + agent messaging | If enabled |
| 4 PredictHazard (load trained model) | **Predictive ML** | Yes |
| 5 PredictVulnerability (load trained model) | **Predictive ML** | Yes |
| 6 Financial + EP + Accumulation | **Deterministic** | Yes |
| 7 XAI (SHAP/CF) + Briefing agent | ML explain + **Agentic LLM** | No |
| 8 Governance / Audit / HumanGate_2 | Rules + audit | No |

Agents produce structured state; they do not invent loss math.

---

## 5. Explainable AI

| Layer | Mechanism | AI? |
|-------|-----------|-----|
| Local SHAP | TreeExplainer on hazard/vuln models | Predictive ML |
| Loss attribution | Location contribution to tier loss / EP | Deterministic |
| Counterfactuals | Feature ± deltas → Δ prediction / Δ loss | Deterministic |
| Global drivers | Mean \|SHAP\|; housing-class loss share; hotspot TIV | ML + deterministic |
| Narratives | Ollama over **frozen** metrics + SHAP tops | Agentic LLM |
| Model card | Purpose, data, limitations (proxy 12/24), ethics | Deterministic |
| Number discipline | `validate_llm_output` vs engine allowlist | Guardrail |

**Rule:** LLM never invents losses. Validation fail → template fallback + audit event.

---

## 6. Security (kenyaRE-hard — non-negotiable)

| Control | Implementation |
|---------|----------------|
| AuthN | Keycloak (compose) + JWT on every route; Render: Keycloak or OIDC with same RBAC |
| AuthZ | Full RBAC (admin, actuary, underwriter, client_viewer, regulator, data_scientist, auditor) |
| Tenant | `TenantContext`; enforce on portfolio/run IDs |
| Encryption | AES-GCM at rest for PII; `hash_token` for irreversible IDs |
| Prompt defence | Injection detect → 400; sanitize + `<data>` wrap; `SAFE_SYSTEM_PROMPT` |
| Output validation | PII / treaty / number allowlist before any LLM text leaves API |
| Audit | SHA-256 hash chain: upload, train, run, enhance, query, decision, approve |
| PII pipeline | Detect → hash/mask before persist; never return raw address in narratives |
| API hygiene | CORS lockdown, rate limits, max upload, security headers, secrets via env |
| Integrity | Model/curve version hashes; run lineage JSON |

**Tests from day one:** `test_security.py`, `test_prompt_injection.py`, `test_rbac.py`, `test_audit_chain.py`, `test_model_registry.py`.

---

## 7. LLM / Ollama (agentic runtime)

| Setting | Choice |
|---------|--------|
| Runtime | Ollama in Docker / Render private service |
| Models | Small instruct: `qwen2.5:3b-instruct` (default) or `deepseek-r1:1.5b` / `qwen2.5:7b-instruct-q4_K_M` |
| Temperature | 0 for structured agents / narratives |
| **Agent uses** | Free-text→exposure, enrichment reasoning notes, underwriter briefing, `/query` Q&A, human-gate summaries |
| **Non-uses** | Final hazard scores, damage ratios, EP points, premiums (those are ML + cat_core) |

Render: bake Ollama + model into image or sibling service; API uses `OLLAMA_HOST`. Degrade to templates if Ollama down (runs still complete).

---

## 8. Target directory tree (lean)

Aim for **≤ ~30 meaningful source files** outside tests/docs (slightly more than before to fit train/predict + agent graph).

```text
floodtail/
├── apps/
│   ├── api/
│   │   ├── main.py
│   │   ├── deps.py
│   │   ├── middleware/auth.py
│   │   └── routers/
│   │       ├── portfolios.py
│   │       ├── runs.py
│   │       ├── results.py
│   │       ├── explanations.py
│   │       ├── query.py
│   │       ├── models.py          # train / list / pin versions
│   │       └── audit.py
│   └── web/                        # Next.js — EMPTY scaffold only
├── packages/
│   ├── agents/                     # AGENTIC AI
│   │   ├── graph.py                # LangGraph-style state machine
│   │   ├── nodes.py                # validate, pii, geocode, enrich, freetext, brief, query
│   │   └── state.py
│   ├── ml/                         # PREDICTIVE ML
│   │   ├── hazard_train.py
│   │   ├── hazard_predict.py
│   │   ├── vulnerability_train.py
│   │   ├── vulnerability_predict.py
│   │   └── registry.py
│   ├── cat_core/                   # DETERMINISTIC
│   │   ├── exposure.py
│   │   ├── depth.py                # score→depth, RP map
│   │   ├── financial.py
│   │   ├── ep.py
│   │   └── accumulation.py
│   ├── security/
│   │   ├── rbac.py
│   │   ├── prompt_defence.py
│   │   ├── output_validation.py
│   │   ├── encryption.py
│   │   ├── tenant.py
│   │   └── audit_log.py
│   ├── xai/
│   │   ├── shap_local.py
│   │   ├── shap_global.py
│   │   ├── counterfactual.py
│   │   ├── narratives.py
│   │   └── model_card.py
│   └── llm/
│       └── ollama_client.py
├── models/                         # versioned artifacts (gitignored weights)
├── Nairobi_Data/
├── docs/
├── tests/
├── infra/
├── docker-compose.yml
├── pyproject.toml
├── .env.example
└── IMPLEMENTATION_PLAN.md
```

**Delete in migration:** `app.py`, `ui/`, Streamlit refs, Kenya radial `data/demo` as product path.

**Reuse/adapt from `src/`:** loss/EP/accumulation/audit/explainability ideas — rewritten into lean packages (not copied as 25 peers).

---

## 9. API contract (v1)

All authenticated unless noted.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/health` | Liveness (+ ollama + model registry) |
| POST | `/v1/portfolios` | Upload CSV / select built-in Nairobi set / free-text agent |
| GET | `/v1/portfolios/{id}` | Metadata (synthetic flags) |
| POST | `/v1/models/hazard/train` | Train + register hazard model (RBAC: data_scientist/admin) |
| POST | `/v1/models/vulnerability/train` | Train + register vuln model |
| GET | `/v1/models` | List versions / pinned |
| POST | `/v1/runs` | Start pipeline (`hazard_model_version`, `vuln_model_version`, agent flags) |
| GET | `/v1/runs/{id}` | Status + stage lineage |
| POST | `/v1/runs/{id}/approve` | Human gate (RBAC) |
| GET | `/v1/runs/{id}/metrics` | AAL, EP points, tier losses |
| GET | `/v1/runs/{id}/properties` | Per-location losses (paginated) |
| GET | `/v1/runs/{id}/accumulation` | Hotspot / class concentration |
| GET | `/v1/runs/{id}/explanations/*` | SHAP global/local, counterfactuals |
| GET | `/v1/runs/{id}/narrative` | Validated agentic briefing |
| POST | `/v1/runs/{id}/query` | Free-text Q&A with injection defence |
| GET | `/v1/audit` | Chain + `chain_valid` |

Payloads always include: `assumptions_version`, `data_labels`, `hazard_model_version`, `vuln_model_version`.

---

## 10. Phased delivery

### Phase 0 — Clean slate scaffolding
- Remove Streamlit (`app.py`, `ui/`, related tests/docs)
- Create `apps/api`, `apps/web` (empty Next.js), `packages/*` skeleton
- `pyproject.toml`, `docker-compose.yml` (api, postgres, keycloak, ollama), `.env.example`
- Health endpoint green

### Phase 1 — Deterministic Nairobi CAT core
- Exposure loader + DQ + depth/RP map + JRC prior curves
- Financial + EP API on built-in CSV (prior curves only — bootstrap path)
- ASSUMPTIONS.md / METHODOLOGY.md
- Unit tests for monotonic damage, EP reconciliation

### Phase 2 — Predictive ML
- Feature builder (proxy + hotspots + optional OSM)
- Train/register HazardModel + VulnerabilityModel
- Inference wired into runs; baseline-vs-predicted deltas stored
- SHAP local/global + model cards
- Registry integrity tests

### Phase 3 — Agentic AI
- LangGraph-style agent graph (validate/PII/geocode/enrich/freetext/brief/query)
- Prompt defence + output validation on every LLM path
- Human gates + approve endpoint
- Prompt-injection integration tests

### Phase 4 — Hard security + governance
- Keycloak + JWT (no anonymous default role in prod)
- Full RBAC, AES, tenant, hash-chained audit on train/run/query/decide
- Decision evidence + mandatory reason

### Phase 5 — Enrichment & deploy
- OSM/raster enrichment features for ML
- Render: API + Ollama; secrets; healthchecks
- Next.js remains empty until separate UI plan

---

## 11. What we borrow from kenyaRE vs floodtail

| From kenyaRE | From floodtail |
|--------------|----------------|
| RBAC, prompt defence, output validation, tenant, audit chain | Loss / EP / accumulation math ideas |
| LangGraph-style agent stages + Ollama narratives | Typed `AgentResult` + critical halt |
| Hazard/vuln **train + predict** pattern + model registry | Decision evidence + human justification |
| SHAP local/global + counterfactuals | ASSUMPTIONS / MODEL_CARD habit |
| Docker compose + Keycloak + Ollama | — |
| **Skip:** Celery, MinIO medallion, LangSmith, broken stubs | **Skip:** Streamlit, Kenya radial demo, 11-agent UI surface |

---

## 12. Success criteria (E2E backend)

1. Nairobi portfolio run produces **EP curve + tier losses** via API.
2. Synthetic / proxy / assumed values are **labelled** in every metrics payload.
3. **Trained** hazard + vuln models are registered; pinning a version changes predictions → changes losses; delta auditable.
4. **Agentic** free-text exposure and briefing paths work; briefing **cannot** invent numbers.
5. Prompt-injection queries **rejected**; audit chain verifies.
6. RBAC blocks underwriter from train/admin paths; auditor can verify chain.
7. Streamlit gone; Next.js present but feature-empty.
8. File count stays lean; pipeline readable in one sitting.
9. Docs rewritten for Nairobi pluvial + synthetic ML labels.

---

## 13. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Render + Ollama RAM | 1.5B–3B quantized; sibling service; template fallback |
| Synthetic ML labels overclaimed | ASSUMPTIONS + model card; label provenance in registry |
| Agents invent numbers | Output validator + tests; cat_core sole loss authority |
| kenyaRE stub bugs | Re-implement clean modules; no copy of empty encryption |
| Scope / file bloat | Enforce tree in §8; merge before adding files |
| Frontend creep | Next.js empty until API contracts freeze |

---

## 14. Immediate next actions after plan approval

1. Phase 0 scaffolding (delete Streamlit, empty Next.js + FastAPI + compose).
2. Phase 1 deterministic CAT against `Nairobi_Data/exposure_nairobi_with_hazard.csv`.
3. Parallel: security package + failing tests (TDD).
4. Phase 2 train jobs → Phase 3 agent graph.

---

## 15. Open items (defaults)

| Item | Default |
|------|---------|
| Primary Ollama model | `qwen2.5:3b-instruct` |
| Tree library | XGBoost (fallback LightGBM) |
| `D_max` | 4.0 m |
| RP map | §4.1 table |
| Auth on Render | Keycloak if feasible; else OIDC JWT + same RBAC |
| DB | Postgres in compose; SQLite fallback for API-only local |

---

## 16. Hackathon deliverables checklist (Team A problem statement)

| # | Deliverable | How this repo meets it |
|---|-------------|------------------------|
| 1 | End-to-end flood loss pipeline | `cat_core` + `ml` + `agents` via FastAPI `/v1/runs` |
| 2 | Hazard ingestion (proxy/rasters) | `Nairobi_Data/` GeoTIFFs + CSV scores |
| 3 | Documented vulnerability (JRC-adapted) | Housing-class curves + `docs/ASSUMPTIONS.md` |
| 4 | Synthetic exposure labelled | 600-loc CSV; `synthetic=True` in all payloads |
| 5 | Single-scenario loss + EP curve | Tier losses + RP map → EP API |
| 6 | AI that **changes** output | Trained hazard/vuln ML + optional free-text agent |
| 7 | Results interface (non-modeller) | Next.js scaffold now; UI features in roadmap Phase UI |
| 8 | Written note: sources / assumptions / AI | ASSUMPTIONS + METHODOLOGY + MODEL_CARD |
| 9 | Honest real vs assumed labelling | `data_labels` on every metrics response |

**Out of scope (do not build):** treaty layers, real client portfolios, multi-peril, full pluvial hydrology.

---

**Status:** Plan approved for implementation. Phase 0 (Streamlit removal + Next.js/FastAPI scaffold) proceeds; full E2E tracked in `ROADMAP.md`.
