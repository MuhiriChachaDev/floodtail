# FLOODTAIL — Explainability & Mathematical Trace

## Overview

FLOODTAIL provides **deterministic, structured, auditable explanations** for every
underwriting recommendation. All explanations are grounded entirely in empirical
model evidence — no LLMs, no stochastic language generation. Every statement
traces back to a computed metric.

Implementation: [`ExplainabilityEngine`](src/explainability.py)

---

## "Why?" Query Types

The explainability engine supports five structured query types, each returning
a typed dataclass with complete attribution to underlying model evidence.

### 1. `explain_policy(policy_id, evidence)` → `PolicyExplanation`

**Question:** "Why is this policy classified as HIGH/NORMAL risk?"

**Returns:**
| Field | Description |
|-------|-------------|
| `summary_text` | Natural language risk summary citing actual metric values |
| `risk_level` | HIGH or NORMAL based on tail contribution and co-hit rate |
| `drivers` | List of quantified risk drivers with actual values |
| `co_hit_context` | Spatial co-occurrence description |
| `top_events` | Top 3 events with occurrence ID, loss, and event share |
| `recommendation_rationale` | AI recommendation with reasons |

**Risk Classification Logic:**
- `HIGH` if: tail_share > 10% OR tail_contribution > portfolio_aal OR co_hit_rate > 50%
- `NORMAL` otherwise

---

### 2. `explain_price(policy_id, evidence)` → `PriceExplanation`

**Question:** "Why is the technical premium $X?"

**Returns:**
| Field | Description |
|-------|-------------|
| `summary_text` | Premium decomposition narrative |
| `technical_premium` | Final premium amount |
| `expected_loss` | AAL (average annual loss) |
| `tail_risk_charge` | Cost-of-capital charge on tail risk |
| `expense_charge` | Expense loading |
| `rate_on_line_bps` | Premium / insured value in basis points |
| `premium_drivers` | Ordered list of premium components with percentages |
| `formula_decomposition` | Full formula: `Premium = AAL + Tail Charge + Expense` |

---

### 3. `explain_tvar(evidence)` → `TVaRExplanation`

**Question:** "Why is the portfolio TVaR this high?"

**Returns:**
| Field | Description |
|-------|-------------|
| `summary_text` | Portfolio-level tail risk narrative |
| `portfolio_tvar` | TVaR(99.6%) value |
| `portfolio_aal` | Portfolio AAL |
| `tail_years_count` | Number of years in the tail set |
| `top_contributing_regions` | Regions ranked by tail contribution |
| `top_contributing_policies` | Policies ranked by tail contribution |
| `systemic_drivers` | Common event patterns driving tail concentration |

---

### 4. `explain_accumulation(region, evidence)` → `AccumulationExplanation`

**Question:** "Why does this region have high concentration risk?"

**Returns:**
| Field | Description |
|-------|-------------|
| `region` | Region name |
| `summary_text` | Regional concentration narrative with actual values |
| `total_tiv` | Total insured value in region |
| `tiv_share_pct` | Region's share of portfolio TIV |
| `total_aal` | Region's AAL |
| `aal_share_pct` | Region's share of portfolio AAL |
| `tail_contribution` | Region's contribution to portfolio TVaR |
| `tail_share_pct` | Region's share of portfolio tail |
| `co_hit_density` | Description of spatial co-occurrence density |
| `drivers` | Factors contributing to concentration |

> Raises `ValidationError` if the requested region is not in the accumulation data.

---

### 5. `explain_recommendation(policy_id, evidence)` → `RecommendationExplanation`

**Question:** "Why did the system recommend ACCEPT/REVIEW/ESCALATE?"

**Returns:**
| Field | Description |
|-------|-------------|
| `recommendation` | ACCEPT, REVIEW, or ESCALATE |
| `confidence_level` | HIGH, MEDIUM, or LOW |
| `confidence_quadrant` | 4-quadrant classification |
| `summary_text` | Recommendation rationale narrative |
| `primary_reasons` | Ordered list of reason codes |
| `risk_appetite_flags` | Governance rule violations, if any |
| `model_warnings` | Active model and data quality warnings |
| `action_guidance` | Suggested action for the underwriter |

---

## 7-Step Mathematical Trace

`generate_mathematical_trace(policy_id, evidence)` → `MathematicalTrace`

Provides a complete, sequential derivation from raw exposure through to final
premium, grounding every intermediate calculation in actual model output.

### Step Sequence

| Step | Name | Formula | Description |
|------|------|---------|-------------|
| 1 | **Exposure Binding** | `TIV = insured_value` | Raw insured value from portfolio |
| 2 | **Hazard Application** | `Depth = max_flood_depth_m` | Maximum flood depth from hazard model |
| 3 | **Vulnerability Application** | `MDR = f(depth, construction)` | Mean damage ratio from depth-damage curve |
| 4 | **Loss Calculation** | `AAL = simulated_average_annual_loss` | Average annual loss from stochastic simulation |
| 5 | **Tail Allocation** | `TC = empirical_tail_contribution` | Policy's contribution to portfolio TVaR |
| 6 | **Pricing Waterfall** | `Premium = AAL + TailCharge + Expense` | Technical premium decomposition |
| 7 | **Decision Scoring** | `Confidence = f(DQ, SimDepth, VulnCal)` | Multi-factor confidence model output |

### Properties

- **Sequential:** Each step builds on the output of the previous step
- **Deterministic:** Same inputs always produce the same trace
- **Complete:** 7 steps cover the entire actuarial value chain
- **Auditable:** Every step includes:
  - `step_number` and `step_name`
  - `formula` (mathematical relationship)
  - `inputs` (named dictionary of input values)
  - `output_name` and `output_value`
  - `explanation` (human-readable narrative)

### Usage

```python
from src.explainability import ExplainabilityEngine

trace = ExplainabilityEngine.generate_mathematical_trace("POL_DEMO_A", evidence_package)

for step in trace.steps:
    print(f"Step {step.step_number}: {step.step_name}")
    print(f"  Formula: {step.formula}")
    print(f"  Inputs:  {step.inputs}")
    print(f"  Output:  {step.output_name} = {step.output_value}")
    print(f"  Explanation: {step.explanation}")
```

---

## Design Principles

1. **No LLMs:** All explanations are template-based, populated with actual computed values
2. **No hallucination:** Every number cited in an explanation is directly sourced from the model output
3. **Structured output:** All explanations are typed dataclasses, not free-text strings
4. **Auditability:** Explanations are reproducible given the same `DecisionEvidencePackage`
5. **Regulatory readiness:** Explanations meet the transparency requirements for
   "What is the basis for this decision?" queries from regulators, brokers, and cedants
