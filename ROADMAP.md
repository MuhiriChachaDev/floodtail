# FLOODTAIL — Full End-to-End Completion Roadmap

**Goal:** Ship a Team A Nairobi Urban Flood CAT prototype that a reinsurer underwriter can run, explain, and audit — with predictive ML, agentic AI, and a deterministic financial/EP core.

**Problem statement authority:** `Team_A_Nairobi_Problem_Statement.docx`  
**Architecture authority:** `IMPLEMENTATION_PLAN.md`  
**Data:** `Nairobi_Data/`

---

## Current status (checkpoint)

| Item | Status |
|------|--------|
| Streamlit (`app.py`, `ui/`) | **Removed** |
| FastAPI scaffold (`apps/api`) | **Done** — `/v1/health` |
| Next.js empty scaffold (`apps/web`) | **Done** — placeholder only, no product UI |
| Package skeletons (`packages/*`) | **Done** — empty modules |
| Docs rewritten for Nairobi | **Done** |
| Deterministic CAT / ML / agents / security | **Not started** (legacy `src/` still present for reference) |
| Hackathon UI (EP curve, etc.) | **Not started** |

---

## Definition of “fully complete”

A submission is complete when **all** of the following are true:

1. **Pipeline:** Hazard → Vulnerability → Exposure → Financial → EP curve runs on `Nairobi_Data`.
2. **Outputs:** Portfolio loss per tier/RP, EP curve, housing-class breakdown, total TIV.
3. **AI changes output:** Trained hazard and/or vulnerability models (and/or free-text exposure agent) change losses vs baseline; delta auditable.
4. **Honesty:** Synthetic exposure + proxy hazard labelled everywhere; assumptions documented.
5. **XAI:** SHAP and/or deterministic counterfactuals + validated Ollama briefing.
6. **Security:** JWT/Keycloak, RBAC, prompt defence, output validation, AES/hash PII, hash-chained audit.
7. **Interface:** Next.js (or interim API demo page) shows exposure, EP, class breakdown, AI output in &lt;2 minutes.
8. **Written note:** ASSUMPTIONS + METHODOLOGY + MODEL_CARD cover sources, assumptions, AI feature.
9. **Tests:** Core CAT, ML registry, prompt injection, audit chain, API smoke green.
10. **Deploy path:** Documented local compose + Render notes with Ollama.

---

## Phase map (execute in order)

```
P0 Scaffold ✓ → P1 Deterministic CAT → P2 Predictive ML → P3 Agentic AI
    → P4 Security/Governance → P5 Results UI → P6 Enrichment/Deploy → P7 Hackathon polish
```

Legacy `src/` is **reference only** after P1; delete or archive once `packages/cat_core` replaces it.

---

### Phase 0 — Scaffold *(COMPLETE)*

- [x] Delete Streamlit `app.py` and `ui/`
- [x] FastAPI `apps/api` with `/v1/health`
- [x] Empty Next.js `apps/web`
- [x] `packages/*` skeletons, `pyproject.toml`, `docker-compose.yml`, `.env.example`
- [x] Docs retargeted to Nairobi Team A
- [x] Remove Streamlit frontend smoke tests; add `tests/test_api_health.py`

**Exit:** `uvicorn apps.api.main:app` + `GET /v1/health` returns `streamlit: removed`.

---

### Phase 1 — Deterministic Nairobi CAT core *(NEXT)*

**Owns:** `packages/cat_core/`

| Task | Detail | Done when |
|------|--------|-----------|
| 1.1 Exposure loader | Load `exposure_nairobi_with_hazard.csv`; stamp `synthetic=True` | Unit test 600 rows |
| 1.2 Depth / RP map | `depth = score × D_max` (4.0 m); tiers → RP 5/20/50/100/250 | Documented in ASSUMPTIONS |
| 1.3 Vulnerability prior | JRC-adapted curves per `housing_class`; damage ∈ [0, cap] | Monotonicity tests |
| 1.4 Financial engine | `loss = damage_ratio × tiv_kes` per loc × tier | Portfolio totals reconcile |
| 1.5 EP builder | Tier losses → EP points + simple AAL | `/v1/runs` + `/metrics` |
| 1.6 DQ gate | Bbox, TIV&gt;0, housing enum | Failed DQ → FAILED AgentResult |
| 1.7 API | `POST /v1/portfolios`, `POST /v1/runs`, `GET .../metrics`, `.../properties` | OpenAPI works |
| 1.8 Labels | Every metrics payload has `data_labels` | Contract test |

**Hackathon minimum met after P1:** single-scenario + EP curve (without ML yet).  
**Exit:** Built-in Nairobi run returns EP curve JSON; ASSUMPTIONS filled for depth/RP/curves.

---

### Phase 2 — Predictive ML *(REQUIRED for option 3)*

**Owns:** `packages/ml/`

| Task | Detail | Done when |
|------|--------|-----------|
| 2.1 Features | Proxy scores + hotspot distance (+ optional OSM later) | Feature matrix shape stable |
| 2.2 Hazard train | XGBoost/LightGBM; synthetic labels; CLI + `POST /v1/models/hazard/train` | Artifact + SHA-256 registry |
| 2.3 Hazard predict | Load pinned version at run | Losses differ from prior-only baseline |
| 2.4 Vuln train/predict | Regressor on JRC-synthetic labels | Registry entry |
| 2.5 Wire into runs | `hazard_model_version`, `vuln_model_version` on run | Metrics include versions + deltas |
| 2.6 SHAP | Local + global for tree models | `/explanations/*` |
| 2.7 Model card | Auto/write MODEL_CARD fields from registry | File or API |

**Exit:** Toggling model versions changes EP; delta stored; SHAP returns for a sample property.

---

### Phase 3 — Agentic AI *(REQUIRED for option 3)*

**Owns:** `packages/agents/`, `packages/llm/`

| Task | Detail | Done when |
|------|--------|-----------|
| 3.1 Ollama client | Small model (`qwen2.5:3b-instruct`); temp=0 | Health reports ollama up/down |
| 3.2 Agent graph | validate → PII → geocode → enrich → optional free-text → brief → query | State machine tested |
| 3.3 Free-text exposure | LLM → structured rows → schema validate → run CAT | Portfolio composition changes |
| 3.4 Briefing | Frozen metrics only → narrative | Validator rejects invented numbers |
| 3.5 Query endpoint | `POST /v1/runs/{id}/query` | Injection tests pass |
| 3.6 Human gates | Approve features / approve decision | `POST .../approve` |

**Exit:** Free-text path and briefing work with security validators; pipeline completes if Ollama down (template fallback).

---

### Phase 4 — Hard security & governance

**Owns:** `packages/security/`, API middleware

| Task | Detail | Done when |
|------|--------|-----------|
| 4.1 RBAC | Full kenyaRE role matrix on routes | Underwriter cannot train models |
| 4.2 AuthN | Keycloak JWT (compose); prod OIDC/JWT | Unauthenticated → 401 in prod mode |
| 4.3 Prompt defence | detect + sanitize + SAFE_SYSTEM_PROMPT | `test_prompt_injection` green |
| 4.4 Output validation | PII, treaty leak, number allowlist | Hallucinated numbers blocked |
| 4.5 Encryption | AES-GCM + `hash_token` | Roundtrip tests |
| 4.6 Tenant | Enforce tenant on portfolio/run | Cross-tenant 403 |
| 4.7 Audit chain | SHA-256 append-only on train/run/query/decide | `verify_chain` true |
| 4.8 Decisions | Evidence package + mandatory reason | ACCEPT/REVIEW/ESCALATE logged |

**Exit:** Security test suite green; governance demoable via `/v1/audit`.

---

### Phase 5 — Results interface (hackathon UI)

**Owns:** `apps/web/` — **first time product UI is added**

Minimum screens (problem statement § Step 6):

| Screen | Content |
|--------|---------|
| Upload / Run | Select Nairobi built-in or upload CSV; start run; optional free-text |
| Results | Total exposure (TIV), losses at key RPs, **EP chart**, housing-class breakdown |
| AI panel | What ML changed (delta) + validated briefing |
| Assumptions banner | Synthetic / proxy / assumed RP / D_max always visible |
| Explain | Property SHAP / counterfactual (actuary role) |
| Governance | Audit chain verify (auditor role) |

**Exit:** Non-modeller understands outputs in &lt;2 minutes without reading code.

---

### Phase 6 — Enrichment & deploy

| Task | Detail |
|------|--------|
| 6.1 Raster path | Optional `rasterio` sample of GeoTIFFs for custom portfolios |
| 6.2 OSM features | Waterways / drainage signals for hazard ML |
| 6.3 Hotspot miss report | Explicit list of proxy false negatives (Kibera, Westlands, …) |
| 6.4 Compose polish | Pull Ollama model on init; Keycloak realm export |
| 6.5 Render | API + Ollama service; secrets; healthchecks; cold-start docs |
| 6.6 Retire legacy `src/` | Delete or move to `archive/legacy_src/` once unused |

**Exit:** `DEPLOYMENT.md` matches reality; demo runs from clean clone + compose.

---

### Phase 7 — Hackathon polish & submission

| Task | Detail |
|------|--------|
| 7.1 Written note | One-pager or filled ASSUMPTIONS/METHODOLOGY/MODEL_CARD |
| 7.2 DEMO_SCRIPT | Judge walkthrough timed to 5–8 minutes |
| 7.3 Validation report | Re-run tests; update FINAL_VALIDATION_REPORT |
| 7.4 Rubric self-check | Genuine AI Δloss shown; limitations honest; EP readable |
| 7.5 Freeze versions | Pin model artifacts; tag `v1.0.0-nairobi-hackathon` |

**Exit:** Ready to submit working demo + written note.

---

## Suggested calendar (3-day hackathon)

| Day | Focus | Must finish |
|-----|-------|-------------|
| **Day 1** | P1 complete + P2 hazard model train/predict started | EP curve via API |
| **Day 2** | P2 finish + P3 agents (briefing + free-text) + P4 essentials (prompt defence, audit, RBAC light) | AI Δ shown |
| **Day 3** | P5 UI minimum + P6 deploy notes + P7 polish | Judge-ready demo |

If time-constrained: **P1 + hazard ML + briefing agent + assumptions labels + minimal EP UI** beats unfinished security chrome.

---

## Workstream ownership (parallelizable)

| Stream | Phases | Depends on |
|--------|--------|------------|
| **CAT core** | P1 | P0 |
| **ML** | P2 | P1 exposure/features |
| **Agents** | P3 | P1 metrics shape; Ollama |
| **Security** | P4 | Can start stubs in parallel with P1 |
| **UI** | P5 | Stable `/metrics` contract |
| **Deploy** | P6 | API + Ollama images |

---

## API completion checklist

- [x] `GET /v1/health`
- [ ] `POST /v1/portfolios`
- [ ] `GET /v1/portfolios/{id}`
- [ ] `POST /v1/models/hazard/train`
- [ ] `POST /v1/models/vulnerability/train`
- [ ] `GET /v1/models`
- [ ] `POST /v1/runs`
- [ ] `GET /v1/runs/{id}`
- [ ] `POST /v1/runs/{id}/approve`
- [ ] `GET /v1/runs/{id}/metrics`
- [ ] `GET /v1/runs/{id}/properties`
- [ ] `GET /v1/runs/{id}/accumulation`
- [ ] `GET /v1/runs/{id}/explanations/*`
- [ ] `GET /v1/runs/{id}/narrative`
- [ ] `POST /v1/runs/{id}/query`
- [ ] `GET /v1/audit`

---

## Test completion checklist

- [x] `tests/test_api_health.py`
- [ ] CAT: damage monotonic, EP reconcile, synthetic stamp
- [ ] ML: train→registry→predict→Δloss
- [ ] Agents: free-text schema; briefing number allowlist
- [ ] Security: injection, RBAC, encryption, audit chain
- [ ] Integration: full run Nairobi built-in portfolio

Legacy tests under `tests/test_*` that import old Streamlit/`ui` must stay deleted or be rewritten against `packages/`.

---

## Risk burn-down

| Risk | Mitigation phase |
|------|------------------|
| Proxy misses drainage floods | P2 hotspot/OSM features + miss report (P6) |
| LLM invents losses | P3/P4 output validation |
| Scope bloat | Enforce package tree; UI only in P5 |
| Render Ollama RAM | Small quantized model; template fallback |
| Legacy `src/` confusion | Archive in P6; don’t extend |

---

## Immediate next actions (start Phase 1)

1. Implement `packages/cat_core/exposure.py`, `depth.py`, `vulnerability.py`, `financial.py`, `ep.py`.
2. Add `POST /v1/runs` returning tier losses + EP for built-in Nairobi CSV.
3. Write `tests/test_cat_core_nairobi.py`.
4. Do **not** add Next.js product pages until metrics contract is stable (end of P1).

---

## Quick commands (Phase 0)

```bash
# API
cd /home/job/Desktop/projects/floodtail
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
uvicorn apps.api.main:app --reload --port 8000

# Frontend scaffold (empty)
cd apps/web && npm install && npm run dev

# Tests
cd ../.. && pytest tests/test_api_health.py -q
```
