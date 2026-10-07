# EXPLAINABILITY — Nairobi Prototype (kenyaRE-aligned)

XAI for Team A Nairobi Urban Flood CAT. Numbers that reach underwriters or judges must be **engine-sourced** or **explicitly rejected**.

---

## Principles

1. **ML explains predictions; `cat_core` explains money.** SHAP on hazard/vuln trees; loss/EP attribution is deterministic.
2. **LLM narrates frozen facts.** Ollama never invents losses, EP points, AAL, or premiums.
3. **Fail closed on numbers.** Validation fail → template fallback + audit event.
4. **Label honesty.** Narratives and explanation payloads carry `data_labels` (synthetic / proxy / prototype).

---

## Layers

| Layer | Mechanism | Source |
|-------|-----------|--------|
| Local SHAP | TreeExplainer on HazardModel / VulnerabilityModel | Predictive ML |
| Global drivers | Mean \|SHAP\|; housing-class loss share; hotspot TIV | ML + deterministic |
| Loss attribution | Location / class contribution to tier loss and EP | Deterministic |
| Counterfactuals | Feature ± deltas → Δ prediction and/or Δ loss | Deterministic recompute |
| Narratives | Ollama over frozen metrics + SHAP tops | Agentic LLM |
| Model card | Purpose, data, limitations (proxy 12/24), ethics | Deterministic doc / API |
| Number discipline | `validate_llm_output` vs engine allowlist | Guardrail |

---

## SHAP

- **When:** After a successful run with pinned tree models.
- **Local:** Per-location (or sampled) feature contributions to predicted hazard score or damage ratio.
- **Global:** Mean absolute SHAP across sample; surfaced on `GET /v1/runs/{id}/explanations/*`.
- **Honest scope:** Explains **model predictions**, not real flood physics. Synthetic training labels → SHAP reflects that label process.

---

## Counterfactuals

Given a location and baseline features:

1. Apply controlled feature deltas (e.g. housing class, distance-to-hotspot, hazard score).
2. Re-run **predict** (± optional financial step) with the same pinned models.
3. Report Δ prediction and Δ ground-up loss — computed only by ML + `cat_core`.

LLM may summarise the CF table; it may not invent alternate EP curves.

---

## Validated Ollama narratives

**Inputs to the LLM (frozen):**

- Portfolio / run IDs, model versions, `assumptions_version`
- AAL, EP points, tier losses (from metrics)
- Top SHAP features, top accumulating hotspots/classes
- Explicit labels: synthetic exposure, proxy hazard, prototype RP

**Controls (kenyaRE patterns):**

| Control | Behaviour |
|---------|-----------|
| Prompt defence | Injection detect → HTTP 400; sanitize + `<data>` wrap; `SAFE_SYSTEM_PROMPT` |
| Output validation | Strip/reject PII; block treaty-like invent; **number allowlist** |
| Number allowlist | Only floats/ints present in the frozen metrics/SHAP payload (tolerance for formatting) |
| Fail path | Template briefing from metrics JSON; audit `NARRATIVE_VALIDATION_FAILED` |
| Temperature | 0 for briefings / structured agents |

Endpoints: `GET /v1/runs/{id}/narrative`, `POST /v1/runs/{id}/query` (same validation).

---

## What we do not claim

- SHAP ≠ causal flood drivers in Nairobi hydrology  
- Counterfactuals ≠ engineering mitigation ROI  
- Narratives ≠ actuarial sign-off  
- Proxy 12/24 hotspot QA ≠ city-wide validation  

See MODEL_CARD.md and ASSUMPTIONS.md.
