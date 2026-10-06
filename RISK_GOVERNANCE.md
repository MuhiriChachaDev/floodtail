# FLOODTAIL — Risk Governance & Human-in-the-Loop

## Overview

FLOODTAIL enforces a **mandatory human-in-the-loop** governance model.
No underwriting decision is ever auto-executed. Every policy must be reviewed
and explicitly decided by a named human underwriter before it is considered final.

---

## Decision Flow

```
11-Agent Orchestration
        ↓
DecisionEvidencePackage (per policy)
        ↓
Human Underwriter Review
        ↓
  ┌─────┼─────┐
  │     │     │
ACCEPT MODIFY REJECT
  │     │     │
  ↓     ↓     ↓
Audit Record (SHA-256 Hash-Chained)
```

---

## Human Decision Types

| Decision | Requirements | Final Premium |
|----------|-------------|---------------|
| **ACCEPT** | No additional input needed | Original technical premium |
| **MODIFY** | Mandatory: `reason` (non-empty) + `modified_premium` (> 0) | User-specified premium |
| **REJECT** | Mandatory: `reason` (non-empty) | $0.00 |

### Override Reason Enforcement

- `MODIFY` without a reason → `ValidationError` raised, decision blocked
- `MODIFY` without a positive `modified_premium` → `ValidationError` raised, decision blocked
- `REJECT` without a reason → `ValidationError` raised, decision blocked
- `ACCEPT` does not require a reason (implicit approval of AI recommendation)

**No silent overrides are permitted.** Every deviation from the AI recommendation
must be explicitly justified.

Implementation: [`DecisionEngine.record_human_decision()`](src/decision.py)

---

## Decision Confidence Model

### 4-Quadrant Classification

The decision confidence model maps every policy into one of four quadrants:

```
                    HIGH CONFIDENCE
                          │
     LOW_RISK_HIGH_CONF   │   HIGH_RISK_HIGH_CONF
     "Standard Accept"    │   "Accept with Conditions"
                          │
  ────────────────────────┼────────────────────────
                          │
     LOW_RISK_LOW_CONF    │   HIGH_RISK_LOW_CONF
     "Needs More Data"    │   "Escalate / Block"
                          │
                    LOW CONFIDENCE
```

### Confidence Scoring Factors

| Factor | Impact | Condition |
|--------|--------|-----------|
| Data Quality Score ≥ 90% | No penalty | High quality data |
| Data Quality Score 70-89% | −0.20 | Moderate quality |
| Data Quality Score < 70% | −0.45 | Low quality + WARNING |
| Critical Data Issues | −0.15 per issue (max −0.35) | Quality failures |
| Simulation Years < 10,000 | −0.15 | Limited tail sample support |
| Benchmark Vulnerability Curve | −0.10 | Prototype curves in use |

### Confidence Levels

| Score Range | Level |
|-------------|-------|
| ≥ 0.75 | HIGH |
| 0.50 – 0.74 | MEDIUM |
| < 0.50 | LOW |

Implementation: [`DecisionEngine.evaluate_confidence()`](src/decision.py)

---

## Cryptographic Audit Hash Chain

### Architecture

Every underwriting decision is recorded as an immutable `AuditRecord`
linked to its predecessor via SHA-256 cryptographic hash chaining.

```
Genesis: previous_hash = "0" * 64 (64 zero characters)
    ↓
Record 1: decision_hash = SHA-256(genesis_hash | record_1_payload)
    ↓
Record 2: decision_hash = SHA-256(record_1_hash | record_2_payload)
    ↓
Record N: decision_hash = SHA-256(record_N-1_hash | record_N_payload)
```

### Hash Payload

The SHA-256 hash is computed over a pipe-delimited string containing:

```
{previous_hash}|{timestamp}|{run_id}|{policy_id}|{user}|
{recommendation}|{final_decision}|{original_premium:.2f}|{new_premium:.2f}|
{reason}|{model_version}|{data_version}
```

### Properties

- **Append-only:** Records can only be added, never modified or deleted
- **Tamper-evident:** Modifying any record breaks the hash chain
- **Verifiable:** `verify_audit_chain()` recomputes all hashes sequentially
  and detects any inconsistency
- **Genesis-linked:** First record always chains from `GENESIS_HASH`
- **Persisted:** All records stored in SQLite `audit_log` table with foreign key
  to `runs(run_id)`

### Verification

```python
from src.audit_log import AuditManager
from src.database import DatabaseManager

db = DatabaseManager("floodtail.db")
audit = AuditManager(db)

result = audit.verify_audit_chain()
assert result.is_valid is True
print(f"Chain verified: {result.record_count} records, no tampering detected.")
```

If tampering is detected:

```python
result.is_valid        # False
result.broken_index    # Index of the tampered record
result.expected_hash   # What the hash should be
result.actual_hash     # What was found in the database
result.message         # Human-readable description
```

Implementation: [`AuditManager`](src/audit_log.py), [`calculate_decision_hash()`](src/audit_log.py)

---

## Audit Record Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-incrementing record ID |
| `timestamp` | TEXT | ISO 8601 UTC timestamp |
| `run_id` | TEXT | Foreign key to `runs(run_id)` |
| `policy_id` | TEXT | Policy being decided |
| `user` | TEXT | Human underwriter identity (non-empty) |
| `recommendation` | TEXT | AI recommendation (ACCEPT/REVIEW/ESCALATE) |
| `final_decision` | TEXT | Human decision (ACCEPT/MODIFY/REJECT) |
| `original_premium` | REAL | AI-computed technical premium |
| `new_premium` | REAL | Final premium after human decision |
| `reason` | TEXT | Mandatory justification for MODIFY/REJECT |
| `model_version` | TEXT | Model version used |
| `data_version` | TEXT | Data version used |
| `decision_hash` | TEXT | SHA-256 hash of this record |
| `previous_hash` | TEXT | SHA-256 hash of preceding record |

---

## User Identity Requirements

- User identity (`user`) is **mandatory** on all decisions
- Empty or whitespace-only user strings → `ValidationError`
- User identity is included in the SHA-256 hash payload
- All decisions are fully attributable to a named individual
