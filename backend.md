# FLOODTAIL — Backend Implementation Guide (E2E)

**Goal:** Ship a location-flexible FastAPI backend that an underwriter can use to ingest a portfolio, run hazard/vulnerability ML, get grounded EP/capital numbers, and receive an **actionable insight** (insured count + set-aside band + what to do next).

**Authority:** `flowchart.md` (product flow) · `ASSUMPTIONS.md` (modelling defaults) · this file (build order).

**AI posture:** LangGraph + LangChain agents orchestrate; predictive ML follows a **standard ML pipeline**; money figures may appear in LLM text only if produced by analysis tools (never guessed).

---

## 0. Success criteria (backend done)

1. Underwriter uploads **any** valid portfolio (Nairobi starter or custom) → ingest stats (`#houses`, TIV, location label).
2. Hazard + vulnerability models follow: **data → features → train → evaluate → tune → infer**.
3. Run produces EP curve, AAL, accumulation, **capital set-aside band** (floor / central / ceiling).
4. `GET /v1/runs/{id}/insight` returns actionable `ACCEPT|REVIEW|ESCALATE` with cited numbers.
5. Prompt injection rejected; invented KES blocked; audit chain verifies.
6. Tests green for CAT math, ML registry, agents, security smoke.

---

## 1. Target layout

```text
apps/api/
  main.py
  deps.py
  settings.py
  store.py                      # in-memory first; Postgres later
  routers/
    health.py                   # exists
    portfolios.py
    runs.py
    models.py
    insight.py                  # or under runs
    explanations.py
    query.py
    audit.py
  middleware/
    auth.py

packages/
  cat_core/                     # grounded math tools (thin)
    exposure.py
    depth.py
    vulnerability_prior.py      # JRC-style priors (labels + fallback)
    financial.py
    ep.py
    capital.py                  # set-aside band
    accumulation.py
    types.py

  ml/                           # STANDARD ML PIPELINE
    data/
      loaders.py                # load / split / label provenance
      labels.py                 # synthetic label builders (honest)
    features/
      builder.py                # feature engineering
      schema.py                 # feature contract
    hazard/
      train.py
      evaluate.py
      tune.py
      infer.py
    vulnerability/
      train.py
      evaluate.py
      tune.py
      infer.py
    registry.py                 # version + SHA-256 + metrics.json
    pipeline.py                 # orchestration: data→…→infer

  agents/                       # LangGraph
    state.py
    graph.py
    nodes/
      schema_map.py
      dq_pii.py
      enrich.py
      freetext.py
      gates.py
      invoke_ml.py
      invoke_math.py
      insight.py
      briefing.py
      query.py
    tools/                      # LangChain tools wrapping ml + cat_core
      portfolio_tools.py
      ml_tools.py
      math_tools.py
      audit_tools.py

  llm/
    ollama_client.py

  security/
    rbac.py
    prompt_defence.py
    output_validation.py
    encryption.py
    tenant.py
    audit_log.py

  xai/
    shap_local.py
    shap_global.py
    counterfactual.py
    model_card.py

models/                         # artifacts (gitignored weights)
  hazard/{version}/
  vulnerability/{version}/

tests/
  test_cat_core_*.py
  test_ml_pipeline_*.py
  test_agents_*.py
  test_insight_*.py
  test_security_*.py
  test_api_*.py
```

Install extras when needed:

```bash
pip install -e ".[ml,llm,security,geo,dev]"
```

---

## 2. Implementation phases (do in order)

```text
Phase A  Foundation (settings, store, types, health)
Phase B  Grounded math (cat_core) + portfolios/runs/metrics
Phase C  ML pipeline (data→features→train→eval→tune→infer) + registry
Phase D  LangGraph agents + Insight API
Phase E  XAI + security + audit
Phase F  Hardening, docs sync, E2E test
```

Do **not** start agents before math + ML infer exist — Insight needs an allowlist of real numbers.

---

# Phase A — Foundation

### A1. Settings

- [ ] `apps/api/settings.py` via `pydantic-settings` from `.env`
- [ ] Keys: `D_MAX_M`, `RETURN_PERIODS`, `OLLAMA_HOST`, `OLLAMA_PRIMARY_MODEL`, JWT, AES, paths to `Nairobi_Data/` and `models/`
- [ ] Assumptions profile object: `assumptions_version`, capital policy (floor RP, ceiling rule)

### A2. Shared types

- [ ] `packages/cat_core/types.py`: `Portfolio`, `RunConfig`, `TierLoss`, `EPPoint`, `CapitalBand`, `MetricsPayload`, `InsightPackage`, `AgentResult`
- [ ] Every metrics/insight payload includes `data_labels` + `assumptions_version`

### A3. Store

- [ ] `apps/api/store.py`: dict-backed portfolios + runs (UUID)
- [ ] Interface stable enough to swap Postgres later (`get/save portfolio`, `get/save run`)

### A4. Wire app

- [ ] Register empty routers; keep `/v1/health`
- [ ] Test: `tests/test_api_health.py` still green

**Exit A:** settings load; types importable; health OK.

---

# Phase B — Grounded math + portfolio/run API

*Thin tools the agents will call later. Location-agnostic: operate on whatever frame ingest produced.*

### B1. Exposure / ingest stats

- [ ] `exposure.py`: load CSV or built-in Nairobi path
- [ ] Required logical fields (mapped later by agents): `loc_id`, `lat`, `lon`, `housing_class` (or mapped), `tiv_kes`
- [ ] Stamp provenance: `synthetic`, `source`, `location_label`
- [ ] Ingest stats: `n_locations` (insured houses), `total_tiv_kes`, bbox, class counts
- [ ] DQ: TIV > 0, coords finite, class in allowed set (from config, not hardcoded city)

### B2. Depth + RP map

- [ ] `depth.py`: `depth_m = score × D_max` (D_max from assumptions profile)
- [ ] Tier → RP / AEP from profile (default 5/20/50/100/250)

### B3. Vulnerability prior (fallback + label source)

- [ ] `vulnerability_prior.py`: depth–damage curves by housing class (JRC-adapted)
- [ ] Monotonic damage ∈ [0, 1]; used when no ML model pinned **and** as synthetic label generator for training

### B4. Financial + EP + accumulation

- [ ] `financial.py`: `loss = damage_ratio × tiv_kes`; portfolio reconcile
- [ ] `ep.py`: tier losses → EP points + discrete AAL
- [ ] `accumulation.py`: by housing class + optional hotspot/region

### B5. Capital / set-aside band (underwriter-critical)

- [ ] `capital.py` → `CapitalBand { floor_kes, central_kes, ceiling_kes, method, notes }`
- [ ] Defaults (config-driven):
  - **Floor** (avoid under-budgeting): e.g. loss at RP100 or configured PML proxy
  - **Central**: discrete AAL
  - **Ceiling** (avoid over-budgeting): e.g. min(RP250 loss, appetite_cap × TIV)
- [ ] Never invent inside LLM — only this module (or its tool wrapper)

### B6. API

- [ ] `POST /v1/portfolios` — `source=builtin_nairobi` or CSV upload
- [ ] `GET /v1/portfolios/{id}` — metadata + ingest stats
- [ ] `POST /v1/runs` — prior-only path first (`use_ml=false`)
- [ ] `GET /v1/runs/{id}`, `/metrics`, `/properties`, `/accumulation`
- [ ] Stub `/insight` with **template** insight from `CapitalBand` + ingest stats (no LLM yet)

### B7. Tests

- [ ] `tests/test_cat_core_nairobi.py`: 600 rows, monotonic damage, EP reconcile, capital band ordering `floor ≤ central ≤ ceiling` (or documented exception), synthetic stamp

**Exit B:** Built-in Nairobi run returns metrics + template insight with houses + set-aside band.

---

# Phase C — Predictive ML (standard pipeline)

Both **HazardModel** and **VulnerabilityModel** follow the same stages:

```text
Data → Feature engineering → Train → Evaluate → Hyperparameter tuning → Infer
         ↑________________ registry / model card / SHA ________________↑
```

Implement shared plumbing once, then specialize per model.

---

## C0. Shared ML contracts

### C0.1 Feature schema

- [ ] `packages/ml/features/schema.py`: ordered feature names, dtypes, nullable policy
- [ ] Version the feature schema (`feature_schema_version`) and store it with every artifact

### C0.2 Registry

- [ ] `packages/ml/registry.py`
  - Path: `models/{hazard|vulnerability}/{version}/`
  - Files: `model.joblib`, `feature_schema.json`, `metrics.json`, `params.json`, `TRAINING_CARD.json`, `SHA256`
  - Ops: `register`, `load`, `list`, `verify_integrity`, `pin_default`

### C0.3 Pipeline facade

- [ ] `packages/ml/pipeline.py`:
  - `run_training_job(model_type, data_cfg, tune=True) -> RegistryEntry`
  - `predict(model_type, version, frame) -> predictions + lineage`

---

## C1. Data stage

**Owns:** `packages/ml/data/`

| Task | Detail |
|------|--------|
| Load | Portfolio frame (+ hotspots / optional rasters) |
| Clean | Drop/flag nulls, clip scores to [0,1], enforce enums |
| Split | Train / validation / test (e.g. 70/15/15), **grouped** by region or loc if needed to avoid leakage |
| Labels | Build **honest synthetic labels** (document provenance) |
| Provenance | Every dataset version: row count, split seed, label recipe id |

### Hazard labels (synthetic — document as such)

- Proxy tier scores from CSV/raster
- Optional uplift near hotspots / drainage features
- **Never** claim gauge-validated floods

### Vulnerability labels (synthetic)

- Sample depths × housing class → prior curve damage ± controlled noise
- Optional residual target vs prior

### Deliverables

- [ ] `loaders.py`, `labels.py`
- [ ] `tests/test_ml_data.py`: split sizes, no leakage of test ids, label ranges valid

---

## C2. Feature engineering stage

**Owns:** `packages/ml/features/`

Build a **location-agnostic** matrix from ingested columns + enrichments:

| Feature family | Examples | Required? |
|----------------|----------|-----------|
| Exposure | `housing_class` (encoded), `log_tiv`, `floor_area` if present | Yes |
| Hazard proxy | per-tier scores if present | When available |
| Geo enrich | distance_to_nearest_hotspot, local density | When layers ingested |
| Optional | OSM waterway distance, raster sample | Later |

Rules:

- [ ] Same `builder.transform(df)` used at **train and infer**
- [ ] Fit encoders/scalers on **train only**; persist in artifact
- [ ] Missing optional enrichments → explicit default + flag column (no silent Nairobi hardcode)
- [ ] Output: `X` matrix + `feature_names` matching schema version

### Deliverables

- [ ] `builder.py` with `fit` / `transform`
- [ ] `tests/test_ml_features.py`: shape stable, train/infer parity, unknown class handling

---

## C3. Training stage

**Owns:** `packages/ml/hazard/train.py`, `packages/ml/vulnerability/train.py`

| Model | Task | Algorithm (default) | Output |
|-------|------|---------------------|--------|
| Hazard | Predict per-tier susceptibility ∈ [0,1] | XGBoost regressor (multi-output or one model per tier) | `hazard_score_pred_*` |
| Vulnerability | Predict `damage_ratio` ∈ [0,1] | XGBoost / sklearn regressor | `damage_ratio` |

Training job must:

- [ ] Accept `data_cfg` + `feature_schema_version` + random seed
- [ ] Fit feature builder on train split
- [ ] Fit model on train features/labels
- [ ] Write interim artifact dir (before register)
- [ ] Log params + train size + label recipe

CLI and API:

- [ ] CLI: `python -m packages.ml.pipeline hazard train ...`
- [ ] `POST /v1/models/hazard/train`, `POST /v1/models/vulnerability/train` (RBAC later)

---

## C4. Evaluation stage

**Owns:** `evaluate.py` per model

Minimum metrics (store in `metrics.json`):

| Model | Metrics |
|-------|---------|
| Hazard | MAE, RMSE, R² per tier; optional hotspot hit-rate vs proxy |
| Vulnerability | MAE, RMSE, R²; % predictions outside [0,1] before clip; calibration by housing class |

Also:

- [ ] Baseline comparison: prior-only vs model (for vuln); proxy vs model (for hazard)
- [ ] Hold-out test metrics only for go/no-go
- [ ] Fail job if test metric below configured threshold (configurable)

### Deliverables

- [ ] `tests/test_ml_evaluate.py`: metrics written; threshold gate works

---

## C5. Hyperparameter tuning stage

**Owns:** `tune.py` per model

- [ ] Search space documented (e.g. `max_depth`, `learning_rate`, `n_estimators`, `subsample`, `min_child_weight`)
- [ ] Method: sklearn `RandomizedSearchCV` or `GridSearchCV` on **validation** fold (keep test frozen)
- [ ] Objective: minimize MAE / RMSE (config)
- [ ] Cap trials for hackathon (e.g. 20–40); seed everything
- [ ] Persist `best_params` into `params.json`
- [ ] Flag `tuning_enabled: true/false` on registry entry

Optional later: Optuna — not required for v1.

### Deliverables

- [ ] Tune improves or matches default on val set; best params registered
- [ ] `tests/test_ml_tune.py`: smoke with tiny grid + tiny data

---

## C6. Inference stage

**Owns:** `infer.py` per model

- [ ] Load pinned version via registry + SHA verify
- [ ] `transform` with **saved** feature builder (no refit)
- [ ] Predict → clip to [0,1]
- [ ] Return frame + `model_version` + `model_sha` + `feature_schema_version`
- [ ] On integrity fail → critical stage `FAILED`

Wire into runs:

- [ ] `POST /v1/runs` accepts `hazard_model_version`, `vuln_model_version`
- [ ] Store baseline (prior/proxy) vs predicted **delta** on metrics lineage
- [ ] Metrics include both versions

### Deliverables

- [ ] `tests/test_ml_infer.py`: train→register→infer roundtrip; hash mismatch fails
- [ ] `tests/test_ml_delta.py`: toggling model changes EP / capital band

**Exit C:** Train both models with eval+tune; pin; run with ML changes losses vs prior-only.

---

# Phase D — LangGraph / LangChain agents + Insight

### D1. Ollama client

- [ ] `packages/llm/ollama_client.py`: chat, temp=0, timeout, health
- [ ] Degrade flag when Ollama down

### D2. LangChain tools

Wrap existing Python (no duplicated math):

| Tool | Calls |
|------|-------|
| `ingest_portfolio` | exposure loader + stats |
| `schema_map` | column alias → canonical |
| `run_hazard_infer` | ml hazard infer |
| `run_vuln_infer` | ml vuln infer |
| `compute_ep_capital` | cat_core ep + capital |
| `compute_accumulation` | accumulation |
| `get_allowlist` | frozen numbers for LLM |
| `append_audit` | audit event |

### D3. Graph state + nodes

- [ ] `state.py`: portfolio_id, frames, warnings, metrics, allowlist, insight, status
- [ ] Nodes matching `flowchart.md` stages 0–9
- [ ] Critical halt policy in graph edges

### D4. Insight Agent (product output)

Input allowlist must include at least:

- `n_insured_houses`, `total_tiv_kes`, `location_label`
- EP points, AAL
- `capital_band.floor_kes|central_kes|ceiling_kes`
- top concentration drivers
- model versions + delta summary

Output `InsightPackage`:

```text
recommendation: ACCEPT | REVIEW | ESCALATE
insured_houses: int
total_tiv_kes: float
set_aside: {floor, central, ceiling, currency}
why: [1–3 bullets]
next_steps: [1–3 actions]
numbers_source: "tool_allowlist"
narrative: str   # optional prose
```

- [ ] `output_validation`: every money token ∈ allowlist
- [ ] Ollama down → template insight (same numbers)

### D5. API

- [ ] `GET /v1/runs/{id}/insight`
- [ ] `GET /v1/runs/{id}/narrative`
- [ ] `POST /v1/runs/{id}/query` (injection defence)
- [ ] `POST /v1/runs/{id}/approve`

### D6. Tests

- [ ] Free-text → schema fail rejects bad rows
- [ ] Insight validation rejects invented KES
- [ ] Graph completes with Ollama mocked down (template path)

**Exit D:** Full agent graph run; underwriter insight endpoint demoable.

---

# Phase E — XAI + security

### E1. XAI

- [ ] SHAP local/global for tree models
- [ ] Deterministic counterfactuals (feature ± → Δ pred → Δ loss)
- [ ] `GET /v1/runs/{id}/explanations/*`
- [ ] Refresh `MODEL_CARD` fields from registry metrics

### E2. Security

- [ ] RBAC on train / approve / audit routes
- [ ] JWT middleware (Keycloak in compose; stub roles in local prototype mode)
- [ ] Prompt defence on query/freetext
- [ ] AES-GCM + `hash_token` for PII
- [ ] Tenant check on portfolio/run ids
- [ ] SHA-256 audit chain on ingest/train/run/query/decide
- [ ] `GET /v1/audit` + `chain_valid`

### E3. Tests

- [ ] `test_prompt_injection.py`, `test_rbac.py`, `test_audit_chain.py`, `test_output_validation.py`

**Exit E:** Security suite green; explanations return for sample property.

---

# Phase F — E2E hardening

- [ ] One integration test: upload → train → run → metrics → insight → approve → audit verify
- [ ] Health reports: nairobi/data path, ollama up/down, registry present
- [ ] Sync `ROADMAP.md` / `ASSUMPTIONS.md` if capital-band defaults change
- [ ] Update `DEMO_SCRIPT.md` for insight-first walkthrough
- [ ] Do **not** build Next.js product UI in this backend track

**Exit F:** `pytest` green; demo script runnable against API only.

---

## 3. ML pipeline checklist (per model)

Use this for **Hazard** and **Vulnerability** alike:

| Stage | Hazard | Vulnerability | Artifact / proof |
|-------|--------|---------------|------------------|
| **Data** | Load proxy/hotspot labels, split | Load prior-synthetic labels, split | `data_manifest.json` |
| **Features** | Fit/transform builder | Fit/transform builder | `feature_schema.json` + encoders |
| **Train** | Fit XGBoost | Fit regressor | `model.joblib` |
| **Evaluate** | Test MAE/RMSE/R² | Test MAE/RMSE/R² + class calib | `metrics.json` |
| **Tune** | Randomized search on val | Randomized search on val | `params.json` (`best_params`) |
| **Infer** | Registry load + predict + clip | Registry load + predict + clip | run lineage + SHA |

Promotion rule: register only if evaluation gates pass; pin explicitly (no silent retrain on run).

---

## 4. API completion order

| Order | Endpoint | Phase |
|------:|----------|-------|
| 1 | `GET /v1/health` | A (exists) |
| 2 | `POST/GET /v1/portfolios` | B |
| 3 | `POST/GET /v1/runs` | B |
| 4 | `GET /v1/runs/{id}/metrics` | B |
| 5 | `GET /v1/runs/{id}/properties` | B |
| 6 | `GET /v1/runs/{id}/accumulation` | B |
| 7 | `GET /v1/runs/{id}/insight` | B stub → D full |
| 8 | `POST /v1/models/*/train` + `GET /v1/models` | C |
| 9 | `GET /v1/runs/{id}/explanations/*` | E |
| 10 | `GET /v1/runs/{id}/narrative` | D |
| 11 | `POST /v1/runs/{id}/query` | D |
| 12 | `POST /v1/runs/{id}/approve` | D/E |
| 13 | `GET /v1/audit` | E |

---

## 5. Suggested coding slices (day-by-day)

| Slice | Ship |
|-------|------|
| Day 1a | Phase A + B1–B5 (math + capital band) |
| Day 1b | B6–B7 API + tests (prior-only Nairobi E2E) |
| Day 2a | C1–C3 data/features/train + registry |
| Day 2b | C4–C6 eval/tune/infer wired into runs + delta |
| Day 3a | D1–D4 LangGraph + Insight Agent |
| Day 3b | E security essentials + F integration test |

If timeboxed: **B + hazard ML (partial C) + template insight** still demo underwriter value; full tune/agents next.

---

## 6. Explicit non-goals (backend v1)

- Next.js product UI
- Extending legacy `src/` Monte Carlo / Streamlit
- Treaty structuring, real client books, multi-peril hydrology
- Silent retrain on every UI/API click
- LLM-generated EP/AAL without tool allowlist

---

## 7. Quick commands

```bash
# env
cp .env.example .env
pip install -e ".[all]"

# API
uvicorn apps.api.main:app --reload --port 8000

# tests
pytest tests/ -q

# train (after Phase C)
python -m packages.ml.pipeline hazard train --tune
python -m packages.ml.pipeline vulnerability train --tune
```

---

## 8. Definition of “underwriter-ready”

A run is underwriter-ready when `/insight` returns:

1. **Insured houses** for the ingested location/book  
2. **Set-aside band** (floor / central / ceiling) from grounded capital tool  
3. **Recommendation + next steps** grounded in those numbers  
4. Labels showing what is synthetic / proxy / assumed  

That is the E2E backend finish line.
