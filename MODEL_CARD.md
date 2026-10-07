# MODEL CARD — Nairobi Urban Flood CAT Prototype

**Model suite:** HazardModel + VulnerabilityModel + deterministic `cat_core`  
**Product:** FLOODTAIL Team A Nairobi pluvial hackathon prototype  
**Assumptions version:** `nairobi-pluvial-v1`  
**Card status:** Prototype — not regulatory or underwriting-grade

---

## 1. Intended use

| Intended | Not intended |
|----------|--------------|
| Demo end-to-end Nairobi pluvial CAT via API | Pricing real treaties |
| Train/pin ML that changes predicted hazard & damage | Claiming gauge-validated depths |
| Show EP curve + labelled assumptions | Multi-peril or Kenya-wide catalogue |
| Agentic briefing with validated numbers | Replacing human underwriter decision |
| Teaching / hackathon evaluation of AI + CAT stack | Production claims reserving |

Users: hackathon judges, reinsurer prototype reviewers, developers.  
Out of scope users: production pricing desks without recalibration.

---

## 2. Model details

| Component | Type | Train? | LLM? |
|-----------|------|--------|------|
| HazardModel | Gradient-boosted tree (XGBoost / LightGBM) | Yes | No |
| VulnerabilityModel | Tree / regressor on depth + housing class (+ features) | Yes | No |
| Depth / EP / AAL / accumulation | Deterministic formulas | No | No |
| Agents (ingest, brief, query) | Ollama instruct (e.g. `qwen2.5:3b-instruct`) | No | Yes |

Artifacts: `models/hazard/{version}/`, `models/vulnerability/{version}/` with SHA-256 registry.  
Run payloads store pinned versions and lineage.

---

## 3. Training data

| Source | Role | Honest label |
|--------|------|--------------|
| `exposure_nairobi_with_hazard.csv` (600 locs) | Exposure + starter scores | **Synthetic** |
| `nairobi_pluvial_proxy_*.tif` | Susceptibility targets / features | **Proxy** (0–1) |
| `nairobi_hotspots_geocoded.csv` (24) | Uplift / QA | Named list; proxy ≈ **12/24** |
| Optional OSM waterways | Distance features | OpenStreetMap; completeness UNKNOWN |
| JRC/Huizinga-adapted curves | Vuln prior / synthetic labels | **BENCHMARK** adapted |

Hazard and vulnerability ML labels are **synthetic** (proxy + uplift + prior ± noise). They are **not** Nairobi flood gauges or claims.

---

## 4. Evaluation (prototype expectations)

| Check | Expectation |
|-------|-------------|
| Monotonic damage vs depth (prior / model) | Non-decreasing within housing class (tests) |
| EP reconciliation | Tier losses map consistently to RP table |
| Pinning model version | Changes predictions → changes GU / EP; delta auditable |
| Proxy hotspot QA | Document ~12/24; do not hide misses |
| Narrative validation | Invented numbers rejected; template fallback |

Full quantitative backtest against historical Nairobi floods: **not available** (UNKNOWN calibration).

---

## 5. Limitations & risks

- Proxy rasters miss some drainage-driven hotspots  
- `D_max = 4 m` and RP map are **PROTOTYPE**  
- Synthetic TIV / housing mix ≠ real Nairobi portfolio  
- SHAP explains the synthetic-label model, not physics  
- Small Ollama models may hallucinate prose; numbers are gated  
- Render RAM limits may force 1.5B–3B quantized models or template degrade  

**Ethics:** Do not use outputs to deny coverage or set premiums on real lives without human review, recalibration, and governance (see RISK_GOVERNANCE.md).

---

## 6. Environmental / compute notes

Training: modest CPU/GPU for XGBoost on 600 locations — lightweight.  
Inference: per-run predict + optional SHAP.  
LLM: local Ollama; default small instruct; temperature 0 for structured paths.

---

## 7. Citation / provenance

- Exposure & proxy kit: `Nairobi_Data/` (hackathon starter; synthetic)  
- Vulnerability prior: JRC / Huizinga depth–damage literature (adapted)  
- Architecture & security patterns: kenyaRE-hard (RBAC, prompt defence, audit)  
- Register: ASSUMPTIONS.md · Methodology: METHODOLOGY.md · XAI: EXPLAINABILITY.md

Update this card when model versions or label provenance change.
