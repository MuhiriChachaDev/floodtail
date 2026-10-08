# FLOODTAIL — System Backend vs Team A Problem Statement

**Problem statement:** `Team_A_Nairobi_Problem_Statement.docx`  
**Code root:** `apps/api` + `packages/{cat_core,ml,agents,llm,security,xai}`  
**Assumptions register:** `ASSUMPTIONS.md` (`nairobi-pluvial-v1`)  
**Status:** Backend Phase F (CAT core + ML + LangGraph + security/XAI APIs). Product results UI not built.

This document explains (1) how a **real CAT model** is built and how FLOODTAIL follows that process, (2) **exactly where** the vulnerability / damage function lives, (3) a **full traceability map** from every problem-statement requirement to code, and (4) **what is still missing** and what must be added.

---

## 1. What a CAT model is (industry sense)

A **catastrophe (CAT) model** estimates how natural hazards affect insured assets and what financial losses follow. Industry platforms (RMS, Verisk, etc.) and this hackathon prototype share the **same four-stage pipeline**:

```text
HAZARD  →  VULNERABILITY  →  EXPOSURE  →  FINANCIAL ENGINE  →  EP / loss curve
```

| Stage | Plain-English question | Industry meaning |
|-------|------------------------|------------------|
| **Hazard** | Where does the event occur, and how severe is it? | Frequency + severity field (depth, intensity, susceptibility) by location and scenario / return period |
| **Vulnerability** | Given that severity, what % of the asset is damaged? | Depth–damage (or intensity–damage) **function** by construction / occupancy |
| **Exposure** | What is at risk, where, and what is it worth? | Geocoded locations, construction class, TIV / sum insured |
| **Financial engine** | What is the money loss, and how rare is it? | `damage × value` → portfolio loss by scenario → **exceedance probability (EP)** curve / AAL |

A CAT model does **not** only answer “what if a flood happens?” It answers “how large could loss be at a 1-in-100 (≈1% AEP) level?” via return periods and an EP curve.

**How a CAT model is created (process FLOODTAIL follows):**

```text
1. Define peril & geography          → Nairobi County, pluvial / surface-water only
2. Obtain or build a hazard layer    → proxy rasters / CSV scores (0–1 susceptibility)
3. Map hazard to a physical severity → depth_m = score × D_max (documented assumption)
4. Define vulnerability functions    → JRC/Huizinga-adapted curves by housing_class
5. Assemble exposure                 → synthetic portfolio (labelled synthetic)
6. Run financial engine per scenario → loss = damage_ratio × tiv_kes per loc × tier
7. Aggregate → EP / AAL              → five tiers mapped to prototype RPs
8. (Optional) Improve with AI/ML     → hazard/vuln models, free-text exposure, briefing
9. Document assumptions & limits     → ASSUMPTIONS.md, data_labels, model cards
10. Present to underwriters          → metrics / insight API (UI still outstanding)
```

FLOODTAIL is a **working prototype CAT model** for Nairobi pluvial flood: deterministic core in `packages/cat_core`, optional predictive ML in `packages/ml`, agentic orchestration in `packages/agents`. Agents **orchestrate and narrate**; they do **not** invent loss, EP, AAL, or premium figures.

---

## 2. Vulnerability / damage function — exact location

The problem statement treats **vulnerability function** and **damage function** as the same thing: given flood severity (here: depth in metres), return a **damage ratio** (fraction of TIV damaged), varying by construction / housing class.

### Canonical implementation (prior / deterministic CAT path)

| What | Where |
|------|-------|
| **Curve table (depth → damage by class)** | `packages/cat_core/vulnerability_prior.py` — constant `JRC_ADAPTED_CURVES` (lines 12–55) |
| **Damage function (point evaluation)** | same file — `damage_ratio(depth_m, housing_class)` (lines 78–86) |
| **Apply to full portfolio × all tiers** | same file — `add_damage_ratio_columns(...)` (lines 89–106) |
| **Monotonicity guard** | same file — `assert_monotonic()` (lines 64–75, run at import) |
| **Documented source & adaptation** | `ASSUMPTIONS.md` §4 (V1–V4); `METHODOLOGY.md`; `MODEL_CARD.md` |

**Behaviour (matches §9 Step 2):**

- Damage near zero at low depth; rises through mid-range; approaches a class-specific ceiling (RCC lower than informal iron sheet).
- Piecewise-linear interpolation on published-style depth–damage points (JRC / Huizinga **adapted**, not Kenya claims-calibrated).
- Classes: `informal_iron_sheet`, `semi_permanent`, `permanent_masonry`, `concrete_rcc`.

```text
# Core call chain in a prior-only run
depth.py :: score_to_depth / add_depth_columns
    → vulnerability_prior.py :: damage_ratio / add_damage_ratio_columns
    → financial.py :: add_loss_columns   # loss = damage_ratio × tiv_kes
    → ep.py :: build_tier_losses / build_ep_curve / discrete_aal
```

### Optional ML vulnerability path (still a damage function)

| What | Where |
|------|-------|
| Train | `packages/ml/vulnerability/train.py` — `train_vulnerability_model` (labels from JRC prior ± noise) |
| Infer | `packages/ml/vulnerability/infer.py` — predicts `damage_ratio ∈ [0,1]` |
| Agent node | `packages/agents/nodes/invoke_ml.py` — `node_predict_vulnerability` (prior fallback when `use_ml=false`) |

ML does **not** replace the concept of a damage function; it learns a regressor whose **training labels** come from `vulnerability_prior.damage_ratio`.

### Severity → depth bridge (required before damage function)

Hazard scores are 0–1 susceptibility, **not metres**. Mapping (problem-statement Option: score × max depth):

| What | Where |
|------|-------|
| `depth_m = score × D_max` | `packages/cat_core/depth.py` — `score_to_depth`, `add_depth_columns` |
| Default `D_max = 4.0 m` | `packages/cat_core/assumptions.py` — `AssumptionsProfile.d_max_m` |

---

## 3. CAT pipeline in this system (file map)

```text
┌─────────────────────────────────────────────────────────────────────────┐
│  HAZARD                                                                 │
│  Data: Nairobi_Data/exposure_nairobi_with_hazard.csv                    │
│        Nairobi_Data/nairobi_pluvial_proxy_*.tif (optional rasters)      │
│  Depth map: packages/cat_core/depth.py                                  │
│  Optional ML: packages/ml/hazard/{train,infer}.py → models/hazard/      │
├─────────────────────────────────────────────────────────────────────────┤
│  VULNERABILITY (damage function)                                        │
│  Prior curves: packages/cat_core/vulnerability_prior.py  ★ PRIMARY      │
│  Optional ML: packages/ml/vulnerability/{train,infer}.py                │
├─────────────────────────────────────────────────────────────────────────┤
│  EXPOSURE                                                               │
│  Load/DQ: packages/cat_core/exposure.py                                 │
│  Schema map / free-text: packages/agents/tools/portfolio_tools.py       │
│                          packages/agents/nodes/freetext.py              │
├─────────────────────────────────────────────────────────────────────────┤
│  FINANCIAL ENGINE                                                       │
│  GU loss: packages/cat_core/financial.py                                │
│  EP/AAL:  packages/cat_core/ep.py                                       │
│  Capital: packages/cat_core/capital.py                                  │
│  Accumulation: packages/cat_core/accumulation.py                        │
│  Tool wrapper: packages/agents/tools/math_tools.py :: compute_ep_capital│
├─────────────────────────────────────────────────────────────────────────┤
│  ORCHESTRATION                                                          │
│  LangGraph: packages/agents/graph.py                                    │
│  API: apps/api/routers/{portfolios,runs,models,insight,...}.py          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Default run order (LangGraph nodes):**  
`schema_map` → `dq_pii` → `enrich` → `freetext` → `gate1` → `baseline` → `hazard` → `depth` → `vuln` → `math` → `xai` → `insight` → `governance`

---

## 4. Full problem-statement traceability

Legend: **DONE** = implemented in backend · **PARTIAL** = present but incomplete for submission · **GAP** = not addressed · **OOS** = out of scope per §7

### 4.1 Introduction & problem description (§1)

| Requirement | Status | Where addressed |
|-------------|--------|-----------------|
| Build AI-powered flood model: risk → losses for flood events | **DONE** | End-to-end run via `POST /v1/runs` + `cat_core` + optional ML |
| Four CAT stages: Hazard, Vulnerability, Exposure, Financial | **DONE** | See §2–§3 of this doc; `packages/cat_core/*` |
| Use return periods / EP thinking (not single “what-if”) | **DONE** | Five tiers → RP 5/20/50/100/250 in `assumptions.py`; EP in `ep.py` |
| AI must meaningfully change modelling (not decoration) | **DONE** | Hazard/vuln ML deltas; free-text exposure; insight over allowlisted numbers |
| Open data + synthetic exposure only | **DONE** | `Nairobi_Data/`; `synthetic=True` stamps |

### 4.2 Objectives (§2)

| Objective | Status | Where |
|-----------|--------|-------|
| Ingest hazard data | **DONE** | CSV with scores via `exposure.py`; rasters in `Nairobi_Data/` (lookup for custom portfolios **PARTIAL** — see gaps) |
| Apply vulnerability functions to estimate damage | **DONE** | `vulnerability_prior.py` :: `damage_ratio` / `add_damage_ratio_columns` |
| Assess losses for each property | **DONE** | `financial.py` :: `add_loss_columns` |
| Aggregate property losses by return period | **DONE** | `ep.py` :: `build_tier_losses` / `build_ep_curve` |
| Financial engine → insured loss + loss/RP curve | **DONE** | `financial.py` + `ep.py` + `capital.py`; metrics on `GET /v1/runs/{id}/metrics` |
| AI that materially enhances result | **DONE** | ML path + free-text + insight (see §5 / §6 below) |
| Produce understandable EP curve | **PARTIAL** | JSON EP points exist; **no chart UI** for non-modellers |
| Clearly state assumptions & synthetic use | **DONE** (docs/API) | `ASSUMPTIONS.md`, `data_labels` on payloads; UI banner **GAP** |
| Present results through stakeholder interface | **GAP** | `apps/web` scaffold only; OpenAPI `/docs` interim |

### 4.3 Stakeholders (§3)

| Stakeholder need | Status | Where |
|------------------|--------|-------|
| Underwriters: defensible loss + RP for budgeting | **DONE** (API) | Metrics + capital band + insight `ACCEPT/REVIEW/ESCALATE` |
| Portfolio managers: accumulation | **DONE** | `accumulation.py`; `GET .../accumulation` |
| Judges: modelling + genuine AI + honest limits | **PARTIAL** | Code + ASSUMPTIONS/MODEL_CARD; demo UI & polish incomplete |
| County / disaster bodies | **PARTIAL** | Conceptual only; no public-facing UI |
| Cedants & brokers | **PARTIAL** | Faster quote path via API; no broker product UI |

### 4.4 Current → Desired state (§4–§5)

| Desired-state item | Status | Where |
|--------------------|--------|-------|
| Ingests a hazard dataset | **DONE** | Starter CSV + proxy GeoTIFFs under `Nairobi_Data/` |
| Documented sourced vulnerability/depth-damage function | **DONE** | `vulnerability_prior.py` + ASSUMPTIONS V1 |
| Synthetic portfolio → loss + RP curve | **DONE** | Prior-only or ML run → metrics EP |
| AI that **changes** output | **DONE** | `baseline_delta` on metrics; free-text changes rows |
| Clear real vs assumption in interface | **PARTIAL** | Labels in API/docs; **not** a first-class UI banner |

### 4.5 Constraints & assumptions (§6)

| Item | Status | Where |
|------|--------|-------|
| No Kenya-specific public vuln curves → adapt global | **DONE** | JRC-adapted curves in `vulnerability_prior.py` |
| Exposure must be synthetic & labelled | **DONE** | Ingest stamps; metrics `data_labels` |
| Hazard is proxy (terrain/depression/slope/OSM rivers); 12/24 hotspots | **DONE** (documented) | ASSUMPTIONS H2,H7; TRAINING_CARD limitations; MODEL_CARD |
| Single / discrete scenarios OK (not full stochastic catalogue) | **DONE** | Five discrete tiers + RP map — not 10k-year MC catalogue |

### 4.6 Scope (§7)

| In scope | Status | Where |
|----------|--------|-------|
| Hazard ingestion / documented proxy | **DONE** | `Nairobi_Data/` + ingest |
| Documented vulnerability/depth-damage function | **DONE** | `vulnerability_prior.py` |
| Synthetic exposure portfolio | **DONE** | 600-row starter + upload + free-text |
| Loss engine: ≥1 scenario + EP curve | **DONE** | Five scenarios + EP |
| One AI stage that materially changes output | **DONE** | Hazard ML (pinned) and/or free-text and/or vuln ML |
| Results interface non-modellers understand | **GAP** | Needs Phase 5 UI |
| **Out of scope** (correctly not built) | **OOS** | Treaty/layers, real claims integration, multi-peril, full pluvial hydrology |

### 4.7 Input data (§8)

| Dataset | Status | Path / use |
|---------|--------|------------|
| `nairobi_pluvial_proxy_*.tif` | **DONE** (present) | `Nairobi_Data/`; primary path uses pre-joined CSV; raster sample for arbitrary points **PARTIAL** |
| `nairobi_hotspots_geocoded.csv` | **DONE** | Enrichment + hazard label uplift |
| `exposure_nairobi_with_hazard.csv` | **DONE** | Default builtin portfolio |
| `exposure_nairobi_synthetic.csv` | **DONE** (present) | Alt path without pre-attached scores |
| JRC / Huizinga reference | **DONE** (adapted in code) | Curves in `vulnerability_prior.py`; citation in ASSUMPTIONS |
| External context links (Star, floods, etc.) | **DONE** (docs) | Background only — not runtime |

### 4.8 How to build the model (§9) — step detail

#### Step 1 — Hazard

| Sub-requirement | Status | Exact location |
|-----------------|--------|----------------|
| Option 1: use `exposure_nairobi_with_hazard.csv` | **DONE** | `Nairobi_Data/exposure_nairobi_with_hazard.csv`; load via `packages/cat_core/exposure.py` |
| Option 2: raw proxy rasters + own lookup | **PARTIAL** | Rasters on disk; full `rasterio` sample path for custom portfolios not first-class product |
| Scores are 0–1 susceptibility, not metres | **DONE** | Documented ASSUMPTIONS H2 |
| Decide how score → severity for vuln | **DONE** | `depth_m = score × 4.0` in `packages/cat_core/depth.py` |
| Five severity tiers with clear meaning | **DONE** | `AssumptionsProfile.tier_names` + RP map in `assumptions.py` |
| Optional AI improve hazard | **DONE** | `packages/ml/hazard/train.py` / `infer.py`; artifact `models/hazard/20261007T145848Z/` |

#### Step 2 — Vulnerability

| Sub-requirement | Status | Exact location |
|-----------------|--------|----------------|
| Damage function: severity → % of building value | **DONE** | `packages/cat_core/vulnerability_prior.py` :: `damage_ratio` |
| Shape: low→0, mid rise, ceiling &lt;100% by class | **DONE** | `JRC_ADAPTED_CURVES` in same file |
| Differ by construction type | **DONE** | Four housing classes in curve table |
| Use / adapt JRC depth-damage; state assumptions | **DONE** | Curves + ASSUMPTIONS V1 |
| Map score→damage via depth decision from Step 1 | **DONE** | `depth.py` then `vulnerability_prior.py` |
| Documented vulnerability matrix | **DONE** | Curve table = matrix (class × depth points); applied per tier columns `damage_ratio_{tier}` |

#### Step 3 — Exposure

| Sub-requirement | Status | Exact location |
|-----------------|--------|----------------|
| Synthetic structured portfolio | **DONE** | `exposure.py` + builtin CSV |
| Free-text → structured rows matching schema | **DONE** | `packages/agents/nodes/freetext.py` + `portfolio_tools.build_freetext_candidates` |
| Stamp synthetic | **DONE** | Ingest + metrics labels |

#### Step 4 — Financial engine

| Sub-requirement | Status | Exact location |
|-----------------|--------|----------------|
| Lookup hazard severity per RP/tier | **DONE** | Tier columns on frame; after ML: predicted scores |
| Pass severity through vulnerability function | **DONE** | `add_damage_ratio_columns` or vuln ML infer |
| `loss = damage_ratio × insured value` | **DONE** | `packages/cat_core/financial.py` :: `add_loss_columns` |
| Sum buildings → portfolio loss per scenario | **DONE** | `reconcile_location_losses` |
| Repeat across RPs → EP curve | **DONE** | `packages/cat_core/ep.py` |
| Assign return periods to five tiers (stated assumption) | **DONE** | `assumptions.py` :: `tier_rp_map` (5/20/50/100/250) |
| Capital / budget view for underwriters | **DONE** (extra vs PS min) | `packages/cat_core/capital.py` |

#### Step 5 — AI intelligence layer (required)

| Suggested approach | Status | Exact location |
|--------------------|--------|----------------|
| Free-text exposure ingestion | **DONE** | `nodes/freetext.py`, Ollama client |
| Natural-language risk briefing | **DONE** | `nodes/insight.py`, `nodes/briefing.py`, query router |
| AI-assisted vulnerability research | **PARTIAL** | Prior is fixed in code; LLM curve “research notes” with human patch noted in ASSUMPTIONS A/V4 — **not** a live research agent |
| Hazard layer improvement | **DONE** (ML) | Hazard model trained on proxy + hotspot uplift; OSM optional |
| Evidence AI changed output | **DONE** | `metrics.baseline_delta` (AAL / tier deltas) |

#### Step 6 — Results interface

| Minimum UI item | Status | Notes |
|-----------------|--------|-------|
| Total exposure | **PARTIAL** | In metrics JSON / portfolio stats — **no product screen** |
| Loss at key return periods | **PARTIAL** | In `ep_curve` JSON |
| EP curve chart | **GAP** | No chart component |
| Breakdown by housing class | **PARTIAL** | `accumulation.py` API |
| AI feature output | **PARTIAL** | Insight / explanations JSON |
| Honest real vs assumption labelling in UI | **GAP** | Labels in API only |

### 4.9 Potential solutions (§10) — tech choices used

| Suggestion | Used? | Where |
|------------|-------|-------|
| rasterio/GDAL for raster lookup | **PARTIAL** | Deps/docs; not required for primary CSV path |
| Sigmoid / piecewise depth-damage by class | **DONE** | Piecewise-linear in `vulnerability_prior.py` |
| LLM freeform → exposure rows | **DONE** | Free-text agent |
| Regression to fit/adjust vulnerability | **DONE** | Vuln ML on synthetic prior labels |
| Direct RP interpolation or Monte Carlo | **DONE** (discrete RP) | Discrete EP (not full MC catalogue) |
| Any dashboard framework | **GAP** | Next.js scaffold empty |

### 4.10 Deliverables & evaluation (§11)

| Deliverable | Status | Where |
|-------------|--------|-------|
| Working end-to-end demo | **PARTIAL** | API demo works; judge UI missing |
| Written note: data sources | **DONE** | ASSUMPTIONS, METHODOLOGY, MODEL_CARD, this file |
| Written note: assumptions | **DONE** | `ASSUMPTIONS.md` |
| Written note: AI feature | **DONE** | This file §5–§6; MODEL_CARD; DEMO_SCRIPT |
| Genuine AI + modelling rigour &gt; polish | **PARTIAL** | Strong backend; polish/UI lag |

---

## 5. Models trained (predictive ML)

### HazardModel — trained & pinned

| Item | Detail |
|------|--------|
| Artifact | `models/hazard/20261007T145848Z/` (`model.joblib`, SHA256, metrics, TRAINING_CARD) |
| Code | `packages/ml/hazard/train.py`, `infer.py` |
| Labels | Synthetic proxy scores + hotspot uplift — **not gauges** |
| Effect | Changes per-tier hazard scores → changes depths → damage → EP |

### VulnerabilityModel — trainable; usually train-on-demand

| Item | Detail |
|------|--------|
| Code | `packages/ml/vulnerability/train.py`, `infer.py` |
| Labels | Samples from `damage_ratio` prior ± noise |
| Not pre-pinned in repo by default | Train via `POST /v1/models/vulnerability/train` before `use_ml=true` |

---

## 6. Agents — nodes, tools, AI/security

### Nodes (`packages/agents/graph.py`)

`schema_map` → `dq_pii` → `enrich` → `freetext` → `gate1` → `baseline` → `hazard` → `depth` → `vuln` → `math` → `xai` → `insight` → `governance`

### Tools (`packages/agents/tools/`)

| Module | Calls into |
|--------|------------|
| `portfolio_tools` | `cat_core.exposure` |
| `ml_tools` | hazard/vuln infer + registry |
| `math_tools` | `financial` / `ep` / `capital` / `accumulation` |
| `audit_tools` | `security.audit_log` |

### Explainability (`packages/xai/`)

SHAP local/global, counterfactuals, model cards — via REST (`apps/api/routers/explanations.py`). In-graph `xai` node is currently **SKIPPED**.

### Security (`packages/security/`)

RBAC, prompt injection defence, output number allowlist, PII hash helpers, tenant checks, SHA-256 audit chain.

---

## 7. What works / what does not

### Works (real CAT core)

- Full Hazard → Vulnerability → Exposure → Financial → EP path on Nairobi synthetic data.  
- **Documented damage function** in `vulnerability_prior.py`.  
- Discrete multi-RP EP + AAL + capital band + housing-class accumulation.  
- Hazard ML trained/pinned; vuln ML train/infer path; AI deltas auditable.  
- Free-text exposure + validated insight briefing.  
- Security smoke + Phase F E2E tests.

### Does not work / incomplete for problem statement

- **Results interface** (§9 Step 6 / §7 in-scope UI) — not built.  
- **In-graph XAI** still stub; explanations are on-demand API only.  
- **Vulnerability weights** not always pre-pinned.  
- **Raster-first** custom portfolio path incomplete vs Option 2.  
- In-memory store; prototype auth (not production Keycloak).

---

## 8. GAP LIST — what must be added

Items below are **required or strongly expected by the problem statement** but missing or incomplete in the system today. Treat this as the backlog to close submission risk.

### 8.1 Must add for §9 Step 6 / §7 “results interface” (highest priority)

| Add | Why (problem statement) | Suggested work |
|-----|-------------------------|----------------|
| Underwriter results UI | “Interface a non-modeller can open and understand in under two minutes” | Build `apps/web` screens: total TIV, losses at key RPs, **EP chart**, housing-class breakdown, AI panel |
| Assumptions / data-honesty banner | “Make it clear … real data vs assumption” | Always-visible: synthetic exposure, proxy hazard, D_max, RP map, 12/24 hotspot QA |
| EP curve visualisation | Explicit minimum deliverable | Chart from `GET /v1/runs/{id}/metrics` → `ep_curve` |

### 8.2 Should add for modelling completeness / demo reliability

| Add | Why | Suggested work |
|-----|-----|----------------|
| Pin VulnerabilityModel artifact under `models/vulnerability/` | `use_ml=true` requires both pinned models | Train once; commit or generate in demo script / compose init |
| Wire graph `xai` node | Stage 7 currently SKIPPED | Call SHAP tops into allowlist before insight |
| Optional raster lookup API | §9 Option 2 / §10 geospatial | `rasterio` sample of `nairobi_pluvial_proxy_*.tif` for custom lat/lon portfolios |
| Explicit “proxy miss” hotspot report | §8 limitation (Kibera, Westlands, …) | Endpoint or doc table listing 12 misses used in demo |

### 8.3 Nice-to-have / stretch (not required by §7)

| Add | Why |
|-----|-----|
| Live LLM “vulnerability research” agent | §9 Step 5 bullet; currently curves are fixed in code |
| Full stochastic / Monte Carlo catalogue | §10 optional; discrete EP already satisfies minimum |
| Postgres persistence | Production; memory store OK for hackathon |
| Full Keycloak realm in compose | Prototype JWT/headers exist |

### 8.4 Explicitly do **not** add (out of scope §7)

- Reinsurance treaty / layer / net-of-reinsurance calculations  
- Real policy or claims book integration  
- Multi-peril aggregation  
- Full physically based pluvial hydrology (stretch only)

---

## 9. One-page “does this portray a real CAT model?”

| CAT modelling process step | Present? | Evidence |
|----------------------------|----------|----------|
| Defined peril & study area | Yes | ASSUMPTIONS G1–G3 |
| Hazard layer with severity by scenario | Yes | Five-tier scores + optional Hazard ML |
| Documented severity interpretation | Yes | `depth.py`, D_max=4 m |
| **Vulnerability / damage function by construction** | Yes | **`packages/cat_core/vulnerability_prior.py`** |
| Exposure portfolio with TIV & attributes | Yes | Synthetic CSV + ingest |
| Financial engine: damage × value | Yes | `financial.py` |
| Frequency dimension (RP / AEP) | Yes | Tier→RP map + `ep.py` |
| EP curve output | Yes (API) | Metrics payload |
| Assumptions & synthetic honesty | Yes | ASSUMPTIONS + `data_labels` |
| AI that changes model output | Yes | ML deltas / free-text |
| Stakeholder-facing results UI | **No** | Gap §8.1 |

**Verdict:** The backend is a **real (prototype) CAT model** in structure and calculation. The main problem-statement shortfall is the **results interface**, not the hazard–vulnerability–exposure–financial chain or the damage function.

---

## 10. Quick verification path

```bash
uvicorn apps.api.main:app --reload

# 1) Exposure + prior-only CAT (damage function path)
POST /v1/portfolios   # source=builtin_nairobi
POST /v1/runs         # use_ml=false
GET  /v1/runs/{id}/metrics   # ep_curve, aal, capital_band

# 2) AI that changes losses
POST /v1/models/hazard/train
POST /v1/models/vulnerability/train
POST /v1/runs         # use_ml=true → inspect baseline_delta

# 3) Damage function source of truth
# open packages/cat_core/vulnerability_prior.py  → damage_ratio / JRC_ADAPTED_CURVES
```

---

## Related docs

| Doc | Role |
|-----|------|
| `Team_A_Nairobi_Problem_Statement.docx` | Requirements authority |
| `ASSUMPTIONS.md` | Modelling assumptions register |
| `METHODOLOGY.md` / `MODEL_CARD.md` | Methods & model honesty |
| `AGENTS.md` | Stage criticality contract |
| `flowchart.md` / `backend.md` | Architecture & build order |
| `EXPLAINABILITY.md` | XAI rules |
| `DEMO_SCRIPT.md` | Judge walkthrough |
