# RISK GOVERNANCE — Reinsurer Prototype (Nairobi)

Human-in-the-loop, RBAC, and audit controls for the Team A Nairobi Urban Flood CAT prototype. Security posture: **kenyaRE-hard** (not demo-lite).

---

## Principles

1. **AI recommends; human decides** for underwriting-relevant outcomes.  
2. **Deterministic core owns money numbers**; LLM owns prose only after validation.  
3. **Every material action is auditable** (upload, train, run, enhance, query, decide, approve).  
4. **Synthetic / proxy / prototype labels** travel with every decision package.  
5. Prototype ≠ production authority to bind risk on real portfolios.

---

## Human-in-the-loop

| Gate | When | Who | Required |
|------|------|-----|----------|
| HumanGate_1 | After enrichment / free-text exposure, before ML+financial (if enabled) | underwriter / actuary / admin | Configurable |
| HumanGate_2 | After metrics + appetite; final decision | underwriter / actuary / admin | Mandatory for “accepted” demo decisions |
| Curve patch | LLM proposes vuln parameter change | actuary / admin | Always human-approved |
| Model pin | Promote trained hazard/vuln version | data_scientist / admin | Explicit pin; no silent retrain on click |

Decision API: `POST /v1/runs/{id}/approve` with **mandatory justification** text. Empty reasons rejected.

Appetite engine (deterministic) may emit `ACCEPT` / `REVIEW` / `ESCALATE`; humans override with reason codes.

---

## RBAC

| Role | Typical permissions |
|------|---------------------|
| `admin` | Full; train; pin; config |
| `data_scientist` | Train / list / pin models; read runs |
| `actuary` | Runs, metrics, explanations, approve, curve patches |
| `underwriter` | Portfolios, runs, metrics, narrative, query, approve (not train) |
| `client_viewer` | Read metrics / narrative for assigned tenant only |
| `regulator` | Read audit + metrics; no mutate |
| `auditor` | Read audit chain; verify `chain_valid` |

Enforcement: JWT claims → `packages/security/rbac.py` on every router. TenantContext on portfolio/run IDs.

Tests expected: `test_rbac.py`, `test_prompt_injection.py`, `test_audit_chain.py`.

---

## Audit chain

SHA-256 hash-chained log for:

- Portfolio upload / free-text ingest  
- Model train + register + pin  
- Run start / stage complete / fail  
- Narrative / query (incl. validation fail)  
- Human approve / decision  

Each event: `prev_hash`, `payload_hash`, actor, role, tenant, timestamp, action type.  
`GET /v1/audit` returns chain + `chain_valid`.

Tamper or broken link → `chain_valid=false`; treat as governance fail for demo sign-off.

---

## Security controls (summary)

| Control | Implementation |
|---------|----------------|
| AuthN | Keycloak (compose) / OIDC JWT |
| AuthZ | Full RBAC as above |
| Tenant | Enforce on portfolio/run resources |
| Encryption | AES-GCM for PII at rest; irreversible `hash_token` for IDs |
| Prompt defence | Injection → 400; sanitize; `<data>` wrap |
| Output validation | PII / treaty / **number allowlist** |
| API hygiene | CORS lockdown, rate limits, max upload, security headers |
| Integrity | Model/curve version hashes; run lineage JSON |

---

## Evidence package (per policy / location or portfolio summary)

Minimum contents for HumanGate_2:

- Key metrics (TIV, GU, AAL contrib, tier losses as applicable)  
- Model versions + `assumptions_version` + `data_labels`  
- Appetite recommendation + flags  
- Top SHAP / accumulation drivers (if available)  
- Human justification (on approve)

LLM briefing may accompany the package; **metrics JSON is authoritative**.

---

## Acceptable use for hackathon judges

- Demonstrate gates, RBAC denial (e.g. underwriter blocked from train), and audit verify  
- Show AI changing **inputs or ML predictions**, not inventing EP numbers  
- Disclose synthetic exposure and proxy hazard in every spoken claim  

Do not present outputs as production reinsurance pricing without recalibration.
