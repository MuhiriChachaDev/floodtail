# ASSUMPTIONS — Nairobi Urban Flood CAT (Team A)

Register of modelling assumptions for the Nairobi County pluvial prototype. Every metrics payload should echo `assumptions_version` and `data_labels`.

**Assumptions version:** `nairobi-pluvial-v1`  
**Scope:** Nairobi County only · pluvial (surface-water) · synthetic exposure · proxy hazard

---

## Status taxonomy

| Status | Meaning |
|--------|---------|
| **SUPPLIED** | Present in repo inputs as-is (CSV / GeoTIFF / hotspot list) |
| **VERIFIED** | Checked against a stated external source or internal QA rule |
| **BENCHMARK** | Adapted from published literature / industry prior (cited) |
| **PROTOTYPE** | Working default for the hackathon; not calibrated to Nairobi claims |
| **UNKNOWN** | Not established; treat as gap |

Do not upgrade status without evidence in this register.

---

## 1. Geography & peril

| ID | Assumption | Status | Notes |
|----|------------|--------|-------|
| G1 | Study area = Nairobi County bounding box for DQ | PROTOTYPE | Coords outside bbox → reject / flag |
| G2 | Peril = pluvial / surface-water only | SUPPLIED | No fluvial channel routing, no multi-peril |
| G3 | No full hydrology (rainfall–runoff–inundation) | SUPPLIED | Explicit non-goal |

---

## 2. Exposure

| ID | Assumption | Status | Notes |
|----|------------|--------|-------|
| E1 | 600 locations in `exposure_nairobi_*.csv` | SUPPLIED | Starter kit; not a real portfolio |
| E2 | Every row `synthetic=True` | SUPPLIED | Stamp preserved on all API payloads |
| E3 | `tiv_kes = floor_area_m2 × cost_per_m2_kes` | SUPPLIED | As generated in starter CSV |
| E4 | Housing classes: `informal_iron_sheet`, `semi_permanent`, `permanent_masonry`, `concrete_rcc` | SUPPLIED | Schema enum for vuln model / curves |
| E5 | Free-text → exposure agent rows are synthetic until human-approved | PROTOTYPE | Agentic path; schema-validated |

---

## 3. Hazard (proxy + ML)

| ID | Assumption | Status | Notes |
|----|------------|--------|-------|
| H1 | Five severity tiers: common, occasional, moderate, severe, extreme | SUPPLIED | Columns + matching GeoTIFFs |
| H2 | Proxy rasters / CSV scores ∈ [0, 1] = relative susceptibility, not metres | SUPPLIED | `Nairobi_Data/nairobi_pluvial_proxy_*.tif` |
| H3 | Depth mapping: `depth_m = hazard_score_pred × D_max` | PROTOTYPE | Linear; no stage-discharge |
| H4 | `D_max = 4.0 m` | PROTOTYPE | Documented default; configurable |
| H5 | Return-period map (see table below) | PROTOTYPE | Discrete EP; not a stochastic catalogue |
| H6 | 24 named hotspots from government lists (geocoded) | SUPPLIED | `nairobi_hotspots_geocoded.csv` |
| H7 | Proxy QA: ≈ **12 / 24** hotspots align with elevated proxy signal | VERIFIED | Known miss: drainage-driven / cold-proxy areas |
| H8 | Hazard ML labels = proxy scores + hotspot uplift + optional OSM drainage uplift | PROTOTYPE | **Synthetic labels** — not flood gauges |
| H9 | Optional OSM waterway distance features | PROTOTYPE | Enrichment only when cited in run lineage |

### Return-period map (PROTOTYPE)

| Tier | Assumed RP (years) | Approx. AEP |
|------|--------------------|-------------|
| common | 5 | 0.20 |
| occasional | 20 | 0.05 |
| moderate | 50 | 0.02 |
| severe | 100 | 0.01 |
| extreme | 250 | 0.004 |

---

## 4. Vulnerability

| ID | Assumption | Status | Notes |
|----|------------|--------|-------|
| V1 | Prior depth–damage curves: JRC / Huizinga-adapted by `housing_class` | BENCHMARK | Adapted for Nairobi housing typology; not Kenya claims-calibrated |
| V2 | Vulnerability ML trained on synthetic labels from prior (± noise / class modifiers) | PROTOTYPE | May predict residual vs prior |
| V3 | `damage_ratio = clip(model.predict(...), 0, 1)` | PROTOTYPE | Inference only; no LLM in numeric path |
| V4 | LLM curve “research notes” require human-approved parameter patch | PROTOTYPE | Never silent curve overwrite |

---

## 5. Financial / EP (deterministic)

| ID | Assumption | Status | Notes |
|----|------------|--------|-------|
| F1 | `ground_up_loss = damage_ratio × tiv_kes` | SUPPLIED | Multiply is deterministic |
| F2 | EP curve from discrete tier losses + RP map | PROTOTYPE | Not 10k-year Kenya Monte Carlo |
| F3 | AAL ≈ Σ (AEP_tier × tier_portfolio_loss) over discrete RPs | PROTOTYPE | Documented discrete approximation |
| F4 | LLM never emits loss / EP / AAL / premium | SUPPLIED | Hard boundary + output allowlist |
| F5 | Optional light MC only for uncertainty bands | PROTOTYPE | Not product core |
| F6 | Single-layer XL: `recovery = min(limit, max(0, gross − attachment))`; `net = gross − recovery` | PROTOTYPE | Default attachment 5% TIV, limit 15% TIV; not a multi-layer programme |
| F7 | Technical premium = gross AAL × load factor (default 1.25) | PROTOTYPE | Indication only; human approval required |

### Capital / set-aside band (PROTOTYPE)

Config keys: `capital_floor_rp`, `capital_ceiling_rp`, `capital_ceiling_tiv_fraction` (see `packages/cat_core/assumptions.py` / `.env`).

| ID | Assumption | Status | Notes |
|----|------------|--------|-------|
| C1 | Floor = portfolio loss at RP **100** (severe tier) | PROTOTYPE | Avoid under-budgeting; `floor_return_period=100` |
| C2 | Central = discrete AAL | PROTOTYPE | May sit below floor — expected for discrete EP |
| C3 | Ceiling = min(loss at RP **250**, `ceiling_tiv_fraction × TIV`) | PROTOTYPE | Default fraction `1.0`; currency `KES` |
| C4 | Guarantee `floor_kes ≤ ceiling_kes` (clamp if needed) | SUPPLIED | Documented in capital tool notes |
| C5 | Insight `set_aside` cites this band only — never LLM-invented KES | SUPPLIED | Allowlist from `cat_core` |

---

## 6. AI / security defaults

| ID | Assumption | Status | Notes |
|----|------------|--------|-------|
| A1 | Primary Ollama model: `qwen2.5:3b-instruct` (or documented swap) | PROTOTYPE | Temp 0 for structured / narrative agents |
| A2 | Tree library: XGBoost (LightGBM fallback) | PROTOTYPE | Version pinned in model registry |
| A3 | Number allowlist from `cat_core` + SHAP tops only | SUPPLIED | kenyaRE-style `validate_llm_output` |
| A4 | Auth: Keycloak JWT + full RBAC in compose / prod | PROTOTYPE | No anonymous default role in prod |

---

## 7. Explicit unknowns

| ID | Gap | Status |
|----|-----|--------|
| U1 | Nairobi gauge / claims calibration of depths and curves | UNKNOWN |
| U2 | True RP–severity relationship for city pluvial events | UNKNOWN |
| U3 | Real TIV / construction distribution vs synthetic kit | UNKNOWN |
| U4 | Drainage network completeness vs OSM | UNKNOWN |

---

## Labelling rule

Any API `metrics` / `narrative` / evidence payload must carry:

- `data_labels`: e.g. `synthetic_exposure`, `proxy_hazard`, `prototype_rp_map`, `synthetic_ml_labels`, `jrc_adapted_curves`
- `hazard_model_version`, `vuln_model_version`, `assumptions_version`

If a value is missing a label, treat it as **UNKNOWN** until classified here.
