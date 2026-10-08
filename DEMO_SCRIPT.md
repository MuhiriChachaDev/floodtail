# DEMO SCRIPT — Team A Nairobi (insight-first, API only)

Judge-facing walkthrough. **No Next.js product UI** in this backend track — demo against FastAPI `/docs` or `curl`.

**Timebox:** ~6–8 minutes  
**Data:** `Nairobi_Data/exposure_nairobi_with_hazard.csv` (600 synthetic buildings)  
**Goal:** Show an underwriter **insured count + set-aside band + what to do next**, with EP/ML/audit behind it.

Prototype headers (when `ENV=prototype`): `X-Floodtail-Role`, `X-Floodtail-Actor`, `X-Floodtail-Tenant`.

```bash
export API=http://localhost:8000
export UW="-H X-Floodtail-Role:underwriter -H X-Floodtail-Actor:demo-uw"
export SCI="-H X-Floodtail-Role:data_scientist -H X-Floodtail-Actor:demo-ds"
export AUD="-H X-Floodtail-Role:auditor -H X-Floodtail-Actor:demo-aud"
```

---

## 0. Framing (20 s)

> “Nairobi County pluvial flood CAT. Exposure is **synthetic**; hazard is **proxy**. ML changes scores; agents brief; **money stays in `cat_core`**. The underwriter deliverable is `/insight` — houses, set-aside band, recommendation.”

Point at `ASSUMPTIONS.md` capital section (floor RP100 / ceiling RP250).

---

## 1. Health (30 s)

```bash
curl -s $API/v1/health | jq '{status, phase, nairobi_data_ok, ollama_up, registry}'
```

Call out:

- `nairobi_data_ok` — starter CSV path present  
- `ollama_up` — live or degraded (template fallback)  
- `registry.registry_ready` — pinned hazard + vulnerability with SHA OK  

Degraded is fine before first train.

---

## 2. Ingest portfolio (45 s)

Built-in (fastest):

```bash
curl -s -X POST $API/v1/portfolios $UW \
  -F "source=builtin_nairobi" -F "location_label=Nairobi County" | jq
```

Or upload:

```bash
curl -s -X POST $API/v1/portfolios $UW \
  -F "source=upload" -F "location_label=Nairobi County" \
  -F "file=@Nairobi_Data/exposure_nairobi_with_hazard.csv" | jq
```

Export `PID` from `portfolio.id`. Say: **600 houses**, `synthetic=True`, housing classes stamped.

---

## 3. Train / pin ML (90 s) — AI that changes output

```bash
curl -s -X POST $API/v1/models/hazard/train $SCI \
  -H "Content-Type: application/json" \
  -d '{"tune":false,"n_iter":3,"seed":7}' | jq '{version, pinned, metrics}'

curl -s -X POST $API/v1/models/vulnerability/train $SCI \
  -H "Content-Type: application/json" \
  -d '{"tune":false,"n_iter":3,"seed":7}' | jq '{version, pinned, metrics}'

curl -s $API/v1/health | jq '.registry'
```

Optional: underwriter tries train → **403**. Labels are synthetic (proxy + hotspot + JRC prior).

---

## 4. Run → **Insight first** (2 min)

```bash
curl -s -X POST $API/v1/runs $UW \
  -H "Content-Type: application/json" \
  -d '{"portfolio_id":"'"$PID"'","use_ml":true,"force_ollama_down":true}' | jq
```

Export `RID`. Then open the underwriter screen:

```bash
curl -s $API/v1/runs/$RID/insight $UW | jq
```

**Show judges this first:**

1. `insured_houses`  
2. `set_aside` floor / central / ceiling (KES)  
3. `recommendation` + `why` + `next_steps`  
4. `data_labels` / `numbers_source` (`template` if Ollama down)

Then metrics for EP proof:

```bash
curl -s $API/v1/runs/$RID/metrics $UW | jq '{
  n_insured_houses, aal_kes, capital_band, ep_curve,
  hazard_model_version, vuln_model_version, data_labels
}'
```

Call out: capital band matches ASSUMPTIONS C1–C3; EP points at RP 5/20/50/100/250.

```bash
curl -s $API/v1/runs/$RID/accumulation $UW | jq '.accumulation.by_housing_class'
```

---

## 5. Approve + audit (45 s)

```bash
curl -s -X POST $API/v1/runs/$RID/approve $UW \
  -H "Content-Type: application/json" \
  -d '{"decision":"REVIEW","reason":"Demo: set-aside band reviewed against appetite","gate":"gate2"}' | jq

curl -s $API/v1/audit $AUD | jq '{chain_valid, total, event_types: [.events[].event_type]}'
```

`chain_valid: true` — hash-chained ingest / train / run / decision.

---

## 6. Optional spice (if time)

| Demo | Endpoint |
|------|----------|
| Free-text exposure | `POST /v1/runs` with `enable_freetext` + text |
| Narrative | `GET /v1/runs/{id}/narrative` |
| Query | `POST /v1/runs/{id}/query` |
| SHAP / CF | `GET /v1/runs/{id}/explanations/*` |

Remind: invented KES rejected; SHAP explains ML on synthetic labels, not hydrology.

---

## 7. Close (20 s)

| Deliverable | Where |
|-------------|--------|
| Underwriter insight | `/v1/runs/{id}/insight` |
| EP + capital band | `/v1/runs/{id}/metrics` |
| AI Δ | ML versions + `baseline_delta` |
| Honesty | `data_labels` + ASSUMPTIONS.md |
| Governance | approve + `/v1/audit` |
| UI | API/OpenAPI only this track |

**Out of scope:** Next.js product UI, treaties, real books, full hydrology.

---

## Fallback if Ollama is down

Use `"force_ollama_down": true` or leave Ollama off. Runs + EP + capital + **template insight** still work. Say so aloud.
