# DEMO SCRIPT — Team A Nairobi (API / metrics)

Judge-facing walkthrough for the hackathon. **UI is empty** (`apps/web` scaffold only). Demo against **FastAPI** + OpenAPI (`/docs`) or `curl`.

**Timebox:** ~8–10 minutes  
**Data:** `Nairobi_Data/exposure_nairobi_with_hazard.csv` (600 synthetic buildings)

---

## 0. Framing (30 s)

> “Nairobi County pluvial flood CAT: Hazard → Vulnerability → Exposure → Financial → EP curve. Exposure is **synthetic**; hazard is **proxy** GeoTIFF/CSV (~12/24 hotspots align). We train **ML** for hazard and damage, use **Ollama agents** for ingest/briefing, and keep loss/EP **deterministic**. Streamlit is gone; results via API until UI ships.”

Show: `ASSUMPTIONS.md` status line or `data_labels` on a sample metrics JSON.

---

## 1. Health & stack (30 s)

```bash
curl -s http://localhost:8000/v1/health | jq
```

Point out: API up, Ollama status (or template degrade), model registry present.  
No Streamlit window.

---

## 2. Portfolio (1 min)

```bash
# Built-in Nairobi set or upload CSV
curl -s -X POST http://localhost:8000/v1/portfolios \
  -H "Authorization: Bearer $TOKEN" \
  -F "source=nairobi_builtin" | jq
```

Call out: `synthetic=True`, 600 locs, housing classes, five hazard score columns.

---

## 3. Train / pin ML — AI that changes output (2 min)

```bash
curl -s -X POST http://localhost:8000/v1/models/hazard/train \
  -H "Authorization: Bearer $DS_TOKEN" | jq
curl -s -X POST http://localhost:8000/v1/models/vulnerability/train \
  -H "Authorization: Bearer $DS_TOKEN" | jq
curl -s http://localhost:8000/v1/models -H "Authorization: Bearer $TOKEN" | jq
```

Say: labels are **synthetic** (proxy + hotspot uplift + JRC prior). Pinning a version is auditable.

Optional contrast: run with baseline scores vs pinned ML; show delta in metrics lineage.

---

## 4. Run pipeline → EP curve (2 min)

```bash
curl -s -X POST http://localhost:8000/v1/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"portfolio_id":"'$PID'","hazard_model_version":"...","vuln_model_version":"..."}' | jq

curl -s http://localhost:8000/v1/runs/$RID/metrics \
  -H "Authorization: Bearer $TOKEN" | jq
```

Show judges:

- Tier losses  
- EP / RP points (prototype map: 5 / 20 / 50 / 100 / 250)  
- AAL (discrete approximation)  
- `assumptions_version`, `data_labels`, model versions  

```bash
curl -s http://localhost:8000/v1/runs/$RID/accumulation \
  -H "Authorization: Bearer $TOKEN" | jq
```

Hotspot / housing-class concentration.

---

## 5. Agentic path — changes inputs or briefing (1.5 min)

**A. Free-text exposure (optional):** submit short building description → new synthetic rows → re-run → metrics move.

**B. Narrative:**

```bash
curl -s http://localhost:8000/v1/runs/$RID/narrative \
  -H "Authorization: Bearer $TOKEN" | jq
```

Emphasize: numbers in prose match metrics allowlist; injection / invented numbers fail closed.

**C. Query (optional):** ask “what drives extreme tier loss?” — validated Q&A.

---

## 6. Security & governance (1 min)

- Underwriter token on `POST /v1/models/hazard/train` → **403**  
- `POST /v1/runs/$RID/approve` with reason → audit event  
- `GET /v1/audit` → `chain_valid: true`  

---

## 7. Explainability (45 s)

```bash
curl -s http://localhost:8000/v1/runs/$RID/explanations/global \
  -H "Authorization: Bearer $TOKEN" | jq
```

SHAP tops + one counterfactual delta. Remind: explains ML on synthetic labels, not hydrology.

---

## 8. Close (30 s)

Checklist for judges:

| Deliverable | Where shown |
|-------------|-------------|
| E2E pipeline | `/v1/runs` → metrics |
| EP curve | `/v1/runs/{id}/metrics` |
| AI changes output | ML pin delta and/or free-text exposure |
| Assumptions labelled | Payload + ASSUMPTIONS.md |
| Results interface | API now; Next.js later |
| Written note | ASSUMPTIONS / METHODOLOGY / MODEL_CARD |

**Out of scope stated:** treaties, real portfolios, multi-peril, full hydrology.

---

## Fallback if Ollama is down

Runs + EP still work. Narrative returns **template** from metrics. Say so aloud — honesty > theatre.
