# FLOODTAIL — Agentic + ML + Deterministic Stages (Nairobi)

Orchestration for the **Nairobi Urban Flood CAT** rebuild. This replaces the former Kenya-wide Streamlit **11-agent** Monte Carlo surface.

**Runtime:** LangGraph-style state machine in `packages/agents` + predictive ML in `packages/ml` + deterministic math in `packages/cat_core`.  
**LLM:** Ollama only where marked Agentic.  
**Halt:** Critical stage `FAILED` stops the run; non-critical failures warn and continue where safe.

---

## Stage list

| Stage | Name | Type | Critical? | Purpose |
|-------|------|------|-----------|---------|
| 1 | SchemaValidate / PII / Geocode / Enrich | Agentic + rules | Yes | Validate Nairobi schema, detect/hash PII, geocode assist, geo enrichment features |
| 2 | FreeTextExposure (optional) | **Agentic LLM** | No | Free-text → structured synthetic exposure rows → schema check |
| 3 | HumanGate_1 | Human + agent messaging | If enabled | Approve features / exposure before ML + financial |
| 4 | PredictHazard | **Predictive ML** | Yes | Load pinned HazardModel; per-tier susceptibility; store version + deltas |
| 5 | PredictVulnerability | **Predictive ML** | Yes | Load pinned VulnerabilityModel; damage ratios; SHAP-ready |
| 6 | Financial + EP + Accumulation | **Deterministic** | Yes | Depth map, GU loss, EP/AAL, hotspot/class accumulation, optional pricing |
| 7 | XAI + Briefing | ML explain + **Agentic LLM** | No | SHAP/CF compute; validated Ollama narrative |
| 8 | Governance / Audit / HumanGate_2 | Rules + audit | No | Appetite rules, evidence package, approve decision, hash-chain audit |

Agents produce **structured state**. They do **not** invent loss, EP, AAL, or premium math.

---

## Stage details

### 1 — SchemaValidate / PII / Geocode / Enrich

- **Inputs:** Portfolio CSV or built-in Nairobi set; optional enrichment flags  
- **Logic:** Required columns, bbox, TIV > 0, housing class enum; PII detect → hash/mask; geocode assist; distances to hotspots / OSM  
- **Outputs:** Clean feature frame, DQ score, warnings  
- **Failed if:** Empty portfolio, schema fatal, or critical DQ breach  

### 2 — FreeTextExposure (optional)

- **Inputs:** Free-text description (underwriter / demo)  
- **Logic:** Ollama → candidate rows → strict schema validation; stamp `synthetic=True`  
- **Outputs:** Appended / replacement exposure rows  
- **Note:** Materially changes portfolio when enabled; still not a real book  

### 3 — HumanGate_1

- **Inputs:** Features + agent notes  
- **Logic:** RBAC approve endpoint; agent may summarise what will be scored  
- **Outputs:** `approved_features=true` or halt if gate required  

### 4 — PredictHazard

- **Inputs:** Feature frame; `hazard_model_version`  
- **Logic:** Registry load + SHA check; predict per-tier scores; optional baseline-vs-pred delta  
- **Outputs:** `hazard_score_*`, model hash, lineage  
- **Failed if:** Missing pinned model or integrity fail  

### 5 — PredictVulnerability

- **Inputs:** Depths (from scores × `D_max`), housing class, features; `vuln_model_version`  
- **Logic:** Predict `damage_ratio` clipped to [0, 1]  
- **Outputs:** Per-location ratios, model hash  
- **Failed if:** Missing pinned model or integrity fail  

### 6 — Financial + EP + Accumulation

- **Inputs:** Ratios, TIV, RP map, hotspot list  
- **Logic:** `loss = damage_ratio × tiv_kes`; aggregate tiers; EP/AAL; concentration metrics  
- **Outputs:** Metrics payload with `data_labels`, EP points, accumulation tables  
- **Failed if:** Reconciliation or empty loss tables  

### 7 — XAI + Briefing

- **Inputs:** Frozen metrics, models, sample rows  
- **Logic:** SHAP local/global, counterfactuals; Ollama briefing over allowlisted numbers  
- **Outputs:** Explanation artifacts; narrative or template fallback  
- **Non-critical:** Run metrics remain valid if briefing fails validation  

### 8 — Governance / Audit / HumanGate_2

- **Inputs:** Metrics, appetite rules, optional decision  
- **Logic:** Deterministic recommendations; mandatory human reason; SHA-256 audit chain event  
- **Outputs:** `ready_for_human`, decision record, `chain_valid`  

---

## Failure handling

| Type | Behaviour |
|------|-----------|
| Critical stage FAILED | Orchestrator halts; run status `FAILED` / `REVIEW_REQUIRED` |
| Non-critical FAILED | Warning + continue (e.g. narrative template) |
| Ollama down | Agents degrade to templates; ML + `cat_core` still run |
| LLM invents numbers | Output validator rejects → template + audit event |
| Model registry hash mismatch | Predict stages FAILED |

Structured result per stage: `status`, `message`, `warnings`, `data` (typed).

---

## Explicit non-agents

These are **not** LLM agents and must not be replaced by Ollama:

- Hazard / vulnerability **numeric** prediction  
- Depth mapping, GU loss, EP, AAL, accumulation, technical premium  
- Audit hash chain math  
- RBAC enforcement  

---

## Relation to old docs

The previous 11 Streamlit agents (ExposureIntelligence … Governance for Kenya Monte Carlo / TVaR UI) are **retired**. Do not revive Streamlit launch paths or Kenya radial demo as the product description.
