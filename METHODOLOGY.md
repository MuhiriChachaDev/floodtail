# METHODOLOGY — Nairobi Pluvial CAT + ML + Agents

End-to-end methodology for Team A Nairobi Urban Flood CAT. Aligns with `IMPLEMENTATION_PLAN.md`.

**Hard boundary:** Agentic AI may change **inputs** (exposure, enrichment, briefings). Predictive ML may change **hazard scores / damage ratios**. Only `packages/cat_core` may emit **loss, EP, AAL, premium, accumulation math**.

---

## 1. Pipeline overview

```
Exposure (CSV / free-text agent)
    → Schema / PII / Geocode / Enrich          [agentic + rules]
    → PredictHazard (pinned model)            [predictive ML]
    → PredictVulnerability (pinned model)     [predictive ML]
    → Depth map · GU loss · EP · AAL · accum  [deterministic]
    → SHAP / CF · Briefing / Query            [XAI + agentic]
    → Governance · Human gates · Audit        [rules + hash chain]
```

Classic CAT chain realised as: **Hazard → Vulnerability → Exposure → Financial → EP curve**.

---

## 2. Hazard

### 2.1 Features (deterministic / geo)

1. Starter scores from `exposure_nairobi_with_hazard.csv` and/or GeoTIFF sample (`rasterio`).
2. Enrichment: distance to OSM waterways, distance to 24 hotspots, optional DEM/depression flags.
3. Depth:

   ```
   depth_m(tier, loc) = hazard_score_pred(tier, loc) × D_max
   ```

   Default `D_max = 4.0 m` (ASSUMPTIONS.md).

4. Discrete RP / AEP map for five tiers (common → extreme). See ASSUMPTIONS.md.
5. Hotspot QA: report proxy miss rate (~12/24 elevated).

### 2.2 Predictive ML

- **HazardModel:** gradient-boosted tree (XGBoost / LightGBM) predicting per-tier susceptibility ∈ [0, 1].
- **Labels:** synthetic — proxy raster/CSV + hotspot uplift + mild OSM drainage uplift where proxy is cold. Never claimed as gauges.
- **Train:** CLI or `POST /v1/models/hazard/train` → `models/hazard/{version}/` + SHA-256 registry.
- **Infer:** load pinned version; store `hazard_model_version` and baseline-vs-predicted delta for XAI.
- No LLM inside numeric hazard prediction.

---

## 3. Vulnerability

- **Prior:** JRC/Huizinga-adapted depth–damage curves by `housing_class` (BENCHMARK; not claims-calibrated).
- **VulnerabilityModel:** regressor on synthetic labels from prior (± noise / class modifiers); optional residual vs prior.
- **Infer:** `damage_ratio = clip(predict(depth, housing_class, …), 0, 1)`.
- SHAP TreeExplainer for local damage drivers.
- Optional agent: research notes → **human-approved** curve parameter patch only.

---

## 4. Exposure

- CSV loader for Nairobi schema; always stamp `synthetic=True`.
- DQ: Nairobi bbox, TIV > 0, valid housing class, coordinates.
- **Agentic path:** free-text → Ollama → structured rows → schema validation → financial engine (materially changes portfolio when used).
- PII detect / hash before persist.

---

## 5. Financial engine & EP (deterministic / statistical)

| Step | Formula / method |
|------|------------------|
| Ground-up loss | `loss = damage_ratio × tiv_kes` |
| Tier portfolio loss | Sum of location losses at that tier depth |
| EP curve | Map tier losses to assumed RP / AEP |
| AAL | Discrete sum over RP map (prototype) |
| Accumulation | Hotspot / housing-class TIV and loss concentration |
| Pricing (optional) | Deterministic technical premium rules |

Optional light MC for uncertainty bands only — **not** a Kenya-wide 10k-year catalogue.

**LLM never emits these numbers.** Narratives consume a frozen allowlist from the engine.

---

## 6. Agentic AI (Ollama)

| Use | Non-use |
|-----|---------|
| Schema messaging, PII flags, geocode assist | Final hazard scores |
| Enrichment reasoning notes | Final damage ratios |
| Free-text → exposure rows | EP points, AAL, premiums |
| Underwriter briefing, `/query` Q&A | Silent curve overwrite |
| Human-gate summaries | Replacement for `cat_core` |

Runtime: Ollama (`qwen2.5:3b-instruct` default), temperature 0 for structured agents. Degrade to templates if Ollama is down; runs still complete.

Every LLM call: prompt defence + output number validation (see EXPLAINABILITY.md).

---

## 7. Reinsurance decision layer (slim)

- Hotspot / class accumulation views  
- Optional technical premium  
- Deterministic appetite rules → ACCEPT / REVIEW / ESCALATE  
- Evidence package + mandatory human justification → hash-chained audit  

Treaty structuring and real client portfolios are **out of scope**.

---

## 8. Run lineage

Each run stores:

- `assumptions_version`, `data_labels`
- `hazard_model_version`, `vuln_model_version` (+ artifact hashes)
- Stage timestamps and agent/ML/deterministic flags
- Baseline-vs-predicted deltas where applicable
- Human gate approvals and decision reasons

Trace must be sufficient to reproduce metrics given the same pinned models and inputs.
