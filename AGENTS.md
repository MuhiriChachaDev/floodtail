# FLOODTAIL — Multi-Agent Decision Architecture

## Overview

The FLOODTAIL catastrophe engine is orchestrated by **11 specialized, typed agents**
executing sequentially in dependency order. Each agent has:

- **Strictly typed inputs** drawn from upstream agent outputs
- **Deterministic, auditable logic** (no LLMs or stochastic inference)
- **Typed `AgentResult` output** containing status, data, warnings, and human-readable message
- **Controlled failure behaviour**: a `FAILED` status from any critical agent halts the pipeline

The orchestration is executed by [`AgentOrchestrator.run_workflow()`](src/agent_orchestrator.py)
and produces a `WorkflowExecutionResult` containing:
- A complete `AgentWorkflowTrace` (all 11 step records)
- Per-policy `DecisionEvidencePackage` objects for human underwriting review
- Aggregated warnings from all agents

---

## Execution Order

| Step | Agent | Purpose | Halt on Failure |
|------|-------|---------|-----------------|
| 1 | ExposureIntelligenceAgent | Data quality, geocoding, exposure validation | ✅ |
| 2 | HazardAnalysisAgent | Spatial flood footprint and event analysis | ✅ |
| 3 | VulnerabilityReviewAgent | Depth-damage curves and construction modifiers | ❌ |
| 4 | LossAnalysisAgent | ELT/YLT reconciliation and portfolio AAL | ✅ |
| 5 | TailRiskAgent | VaR, TVaR, tail allocation by policy | ✅ |
| 6 | AccumulationAgent | Geographic concentration, HHI, co-hits | ❌ |
| 7 | PricingIntelligenceAgent | Risk-based technical pricing waterfall | ✅ |
| 8 | ScenarioAgent | CRN counterfactual marginal TVaR impacts | ❌ |
| 9 | RiskAppetiteAgent | Deterministic underwriting governance rules | ❌ |
| 10 | DecisionSupportAgent | Evidence package assembly and confidence scoring | ❌ |
| 11 | GovernanceAgent | Trace validation and audit readiness check | ❌ |

> **Note:** Step 5 (TailRiskAgent) must execute before Step 6 (AccumulationAgent)
> because AccumulationAgent requires `tail_dataframe` output from TailRiskAgent.

---

## Agent Reference

### 1. ExposureIntelligenceAgent

**Module:** `src/agent_orchestrator.py`

**Inputs:**
- `portfolio_df: pd.DataFrame` — cleaned portfolio with policy_id, lat, lon, insured_value, property_type, construction_class, region
- `dq_auditor: DataQualityAuditor` (optional)

**Logic:**
- Runs full data quality audit via `DataQualityAuditor.audit()`
- Computes quality score, critical issue count, total TIV, policy count
- Returns `WARNING` if quality score < 80 or critical issues exist
- Returns `FAILED` if portfolio is empty or null

**Outputs:**
- `quality_score`, `policy_count`, `total_tiv`, `critical_issues_count`, `is_clean`

**Permissions:** Read-only access to portfolio data

---

### 2. HazardAnalysisAgent

**Module:** `src/agent_orchestrator.py`

**Inputs:**
- `hazard_df: pd.DataFrame` — spatial hazard footprints (policy_id, occurrence_id, depth_m, ...)

**Logic:**
- Counts affected policies, unique events, mean/max flood depths
- Returns `FAILED` if hazard data is missing or empty

**Outputs:**
- `total_impact_records`, `affected_policies_count`, `unique_event_occurrences`, `mean_affected_depth_m`, `max_flood_depth_m`

**Permissions:** Read-only access to hazard data

---

### 3. VulnerabilityReviewAgent

**Module:** `src/agent_orchestrator.py`

**Inputs:**
- `portfolio_df: pd.DataFrame`

**Logic:**
- Enumerates distinct property types and construction classes in portfolio
- Flags that prototype benchmark vulnerability curves are in use

**Outputs:**
- `curve_version`, `property_types_evaluated`, `construction_classes`, `calibration_status`
- Always emits `BENCHMARK_VULNERABILITY_CURVE` warning

**Permissions:** Read-only access to portfolio metadata

---

### 4. LossAnalysisAgent

**Module:** `src/agent_orchestrator.py`

**Inputs:**
- `elt_df: pd.DataFrame` — Event Loss Table
- `ylt_df: pd.DataFrame` — Year Loss Table

**Logic:**
- Computes total simulated loss, portfolio AAL, max annual loss
- Reconciles ELT total vs YLT total (< 1e-3 tolerance)
- Returns `FAILED` if reconciliation fails or data is missing

**Outputs:**
- `total_simulated_loss`, `portfolio_aal`, `simulation_years`, `elt_records_count`, `max_annual_loss`, `loss_reconciliation_passed`

**Permissions:** Read-only access to loss tables

---

### 5. TailRiskAgent

**Module:** `src/agent_orchestrator.py`

**Inputs:**
- `ylt_df: pd.DataFrame`, `elt_df: pd.DataFrame`, `portfolio_df: pd.DataFrame`
- `confidence: float` (default 0.996 for 1-in-250 return period)

**Logic:**
- Computes VaR and TVaR at specified confidence via `RiskMetricsEngine`
- Allocates tail risk to individual policies via `PolicyTailRiskEngine`
- Validates tail and AAL reconciliation
- Returns `FAILED` if reconciliation fails

**Outputs:**
- `portfolio_aal`, `portfolio_var_996`, `portfolio_tvar_996`, `tail_year_count`
- `tail_allocation` (full `PolicyTailAllocationResult`)
- `tail_dataframe` (DataFrame with per-policy tail metrics)
- `top_policy_contributors` (top 5 by tail contribution)

**Permissions:** Read-only access to loss tables and portfolio

---

### 6. AccumulationAgent

**Module:** `src/agent_orchestrator.py`

**Inputs:**
- `portfolio_df: pd.DataFrame`, `elt_df: pd.DataFrame`
- `tail_dataframe: pd.DataFrame` (from TailRiskAgent)

**Logic:**
- Computes regional and property-type concentration breakdowns
- Calculates HHI, top-1%/5%/10% TIV and loss concentration
- Evaluates spatial co-hit metrics (events hitting multiple policies simultaneously)

**Outputs:**
- `regional_breakdown`, `top_1pct_tiv_share`, `top_1pct_tail_share`, `regional_hhi`
- `accumulation_df`, `co_hit_metrics`

**Permissions:** Read-only access to portfolio, ELT, and tail data

---

### 7. PricingIntelligenceAgent

**Module:** `src/agent_orchestrator.py`

**Inputs:**
- `tail_dataframe: pd.DataFrame` (from TailRiskAgent)
- `coc_rate: float` (cost of capital rate, default 0.10)
- `exp_rate: float` (expense ratio, default 0.10)

**Logic:**
- Computes technical premium = expected_loss + tail_charge + expense
- Validates pricing waterfall reconciliation
- Returns `FAILED` if pricing does not reconcile

**Outputs:**
- `total_technical_premium`, `total_expected_loss`, `total_tail_charge`, `total_expense`
- `pricing_dataframe`, `pricing_reconciled`

**Permissions:** Read-only access to tail allocation data

---

### 8. ScenarioAgent

**Module:** `src/agent_orchestrator.py`

**Inputs:**
- `ylt_df`, `elt_df`, `portfolio_df`, `tail_df`
- `confidence: float`

**Logic:**
- Builds policy-annual-loss matrix (PAL)
- Computes CRN (Common Random Numbers) marginal TVaR for each policy
- Marginal TVaR = Portfolio TVaR − TVaR(Portfolio without policy)

**Outputs:**
- `marginal_results` (list of marginal impact records)
- `pal_matrix` (policy-annual-loss matrix DataFrame)

**Permissions:** Read-only access to loss tables, portfolio, and tail data

---

### 9. RiskAppetiteAgent

**Module:** `src/agent_orchestrator.py`

**Inputs:**
- `tail_records` (from TailRiskAgent's `tail_allocation.policy_records`)
- `marginal_impacts` (from ScenarioAgent)
- `co_hit_metrics` (from AccumulationAgent)

**Logic:**
- Applies deterministic governance rules via `RiskAppetiteRuleEngine`
- Produces per-policy recommendation: `ACCEPT`, `REVIEW`, or `ESCALATE`
- Generates risk flags and reason codes

**Outputs:**
- `total_evaluated`, `accept_count`, `review_count`, `escalate_count`
- `recommendations` (list of `PolicyRecommendation` objects)

**Permissions:** Read-only access to tail, marginal, and co-hit data

---

### 10. DecisionSupportAgent

**Module:** `src/agent_orchestrator.py`

**Inputs:**
- All upstream agent data dictionaries
- `run_id`, `model_version`, `data_version`, `sim_years`

**Logic:**
- Iterates over all policy recommendations
- Assembles a `DecisionEvidencePackage` for each policy containing:
  - Key metrics (insured_value, AAL, tail_contribution, marginal_tvar, technical_premium, etc.)
  - Multi-factor `DecisionConfidence` (4-quadrant model)
  - Complete data quality, hazard, vulnerability, loss, accumulation, tail, pricing, and risk appetite summaries

**Outputs:**
- `evidence_packages: dict[str, DecisionEvidencePackage]`

**Permissions:** Read-only aggregation of all upstream data

---

### 11. GovernanceAgent

**Module:** `src/agent_orchestrator.py`

**Inputs:**
- `trace: AgentWorkflowTrace`
- `evidence_packages: dict[str, DecisionEvidencePackage]`

**Logic:**
- Validates that no upstream steps failed
- Confirms that decision evidence packages were assembled
- Certifies `ready_for_human: True` if all checks pass

**Outputs:**
- `ready_for_human: bool`, `policy_count: int`

**Permissions:** Read-only access to workflow trace and evidence packages

---

## Failure Handling

| Failure Type | Behaviour |
|-------------|-----------|
| Critical agent returns `FAILED` | Orchestrator halts immediately, returns `REVIEW_REQUIRED` status |
| Non-critical agent returns `FAILED` | Warning logged, execution continues |
| Empty/null input data | Agent returns `FAILED` with descriptive message |
| Reconciliation failure | Tail or pricing agent returns `FAILED`, halting pipeline |

All failures produce structured `AgentResult` objects with:
- `status: FAILED`
- `message: str` describing the failure
- `warnings: list[str]` with specific failure codes

The `WorkflowExecutionResult` includes `trace.stopped_at_step` and `trace.failure_reason`
when the pipeline is halted.
