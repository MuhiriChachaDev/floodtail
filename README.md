# FLOODTAIL — Reinsurance Catastrophe & Portfolio Decision Intelligence Platform

> **AI Recommends. Human Decides. Auditable Always.**
> 
> *FLOODTAIL connects catastrophe risk modeling, portfolio accumulation, policy-level tail attribution, uncertainty, technical pricing, explainability, and human underwriting into one governed agentic workflow.*

**Release**: `FLOODTAIL Demo Release v1.0.0-demo`  
**Test Suite**: 128 / 128 Passed (0 Failures, 0 Skips)  
**Supported Runtimes**: Python 3.10 – 3.14 (Tested on Python 3.14.5)  

---

## The Problem
In reinsurance, **one flood does not create one isolated claim**. A single spatial flood inundation event turns dozens or hundreds of individually sound commercial properties into one devastating, correlated portfolio catastrophe.

Traditional underwriting evaluates policies in isolation based on standalone location and asset value. As a result, reinsurers blindly accumulate correlated tail risk in the same geographic flood footprint, discovering the true accumulation only after a catastrophic 1-in-250 year event occurs.

## The Solution
FLOODTAIL transforms raw exposure portfolios into an interactive, portfolio-aware decision process:
1. **10,000-Year Monte Carlo Stochastic Engine**: Evaluates Poisson event arrivals and spatial flood footprints across Kenya.
2. **Euler Policy Tail Allocation**: Exactly decomposes portfolio TVaR (99.6% / 1-in-250 year return period) down to individual policies ($\sum \text{Tail}_k = \text{Portfolio TVaR}$).
3. **Common Random Numbers (CRN) Marginal TVaR**: Evaluates true portfolio contribution holding stochastic realizations constant.
4. **Risk-Based Technical Pricing Waterfall**: Expected Loss + Cost of Capital Tail Charge + Expense Loading.
5. **11-Agent Sequential Governance**: Deterministic, typed agents that validate data quality, compute losses, screen risk appetite, and assemble evidence packages.
6. **Human-in-the-Loop & Cryptographic Audit**: Underwriters review evidence, explore mathematical "WHY" traces, and record decisions with mandatory reasons in an immutable SHA-256 hash-chained log.

---

## Architecture Pipeline

```
EXPOSURE PORTFOLIO (CSV / Parquet)
   │
   ▼
[Step 1] ExposureIntelligenceAgent ─── 11 Data Quality Rules & Geocoding Audit
   │
   ▼
[Step 2] HazardAnalysisAgent ──────── Spatial Footprint Intersection (depth_m)
   │
   ▼
[Step 3] VulnerabilityReviewAgent ──── Depth-Damage Curves & Construction Modifiers
   │
   ▼
[Step 4] LossAnalysisAgent ─────────── ELT (80k+ records) & YLT (10k years) Loss Tables
   │
   ▼
[Step 5] TailRiskAgent ─────────────── Portfolio AAL, VaR, TVaR 99.6% & Euler Allocation
   │
   ▼
[Step 6] AccumulationAgent ─────────── Regional HHI, Spatial Co-Hits & Top-1% Share
   │
   ▼
[Step 7] PricingIntelligenceAgent ──── Actuarial Technical Premium Waterfall
   │
   ▼
[Step 8] ScenarioAgent ─────────────── CRN Counterfactual Marginal TVaR Impact
   │
   ▼
[Step 9] RiskAppetiteAgent ─────────── Deterministic Underwriting Governance Rules
   │
   ▼
[Step 10] DecisionSupportAgent ─────── Multi-Factor Confidence & Evidence Packages
   │
   ▼
[Step 11] GovernanceAgent ──────────── Trace Validation & Audit Certification
   │
   ▼
HUMAN UNDERWRITER (ACCEPT / MODIFY / REJECT with Mandatory Justification)
   │
   ▼
CRYPTOGRAPHIC AUDIT LOG (Append-only SHA-256 Hash Chain in SQLite)
```

---

## 16-Page Enterprise Frontend

Launch via Streamlit:
```bash
streamlit run app.py
```

| Page | Title | Key Interactive Capabilities |
|:---:|:---|:---|
| **01** | **Executive Overview** | Portfolio TIV, AAL, TVaR 99.6%, model status, executive KPI summary |
| **02** | **Portfolio** | Searchable policy table, multi-parameter regional and property filters |
| **03** | **Data Intelligence** | Quality score, IQR outlier detection, schema mapping history |
| **04** | **Agent Control** | 11-agent sequential workflow, execution timings, failure injection |
| **05** | **Flood Risk** | Hazard footprint explorer, mean/max depth inspection by policy |
| **06** | **Accumulation** | Geographic concentration, Regional HHI (3,412), spatial co-hits |
| **07** | **Catastrophe Analytics** | Interactive Plotly OEP vs AEP exceedance curves (log RP scale) |
| **08** | **Tail Risk** | Portfolio VaR & TVaR metrics, policy tail contribution waterfall |
| **09** | **Policy Intelligence** | **Killer A/B comparison** (Policy A vs B), 7-step mathematical WHY trace |
| **10** | **Pricing** | Actuarial waterfall chart, live What-If margin slider |
| **11** | **Scenario Lab** | Common Random Numbers (CRN) counterfactual marginal impacts |
| **12** | **Risk Appetite** | Deterministic rule evaluation (`ACCEPT`, `REVIEW`, `ESCALATE`) |
| **13** | **Decisions** | Decision evidence packages, 4-quadrant confidence, human capture |
| **14** | **Audit** | SHA-256 decision ledger with one-click cryptographic verification |
| **15** | **Methodology** | Scientific disclosure of formulas, loss engines, and assumptions |
| **16** | **Future / 2090** | Demarcated vision: Earth observation, physics-informed AI, digital twins |

---

## Quick Installation & Launch

```bash
# 1. Clone repository
git clone https://github.com/MuhiriChachaDev/floodtail.git
cd floodtail

# 2. Virtual environment setup
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 3. Install requirements
pip install -r requirements.txt

# 4. Launch web application
streamlit run app.py

# 5. Or execute headless CLI bootstrap
python app.py
```

---

## Test Suite Verification

Run all 128 tests:
```bash
pytest -v
```

```
======================= 128 passed in 60.13s (0:01:00) ========================
```

| Test File | Tests | Coverage |
|:---|:---:|:---|
| `tests/test_foundation.py` | 30 | Pydantic schemas, data contracts, config, bootstrap smoke |
| `tests/test_data_layer.py` | 27 | SQLite CRUD, schema mapper, normalizer, quality auditor |
| `tests/test_catastrophe_engine.py`| 22 | Poisson simulator, hazard intersection, vulnerability, ELT/YLT |
| `tests/test_risk_analytics.py` | 18 | AAL, OEP/AEP, VaR/TVaR, Euler allocation, pricing waterfall, CRN |
| `tests/test_agent_workflow.py` | 20 | 11-agent sequential orchestrator, governance, trace validation |
| `tests/test_frontend_smoke.py` | 11 | UI components, 16-page catalogue, Plotly charts, audit verification |

---

## Model Governance & Limitations
- **Prototype Status**: FLOODTAIL is a demonstration decision platform using synthetic hazard fields and international benchmark depth-damage curves.
- **Not Kenya Claims Calibrated**: Does not replace proprietary empirical claims loss calibration from reinsurers.
- **Deterministic AI**: No generative LLM hallucination in financial calculations. Every number reconciles exactly to underlying event tables.
- **Immutable Audit**: Decisions cannot be altered retroactively without breaking the cryptographic hash chain.

---

## Repository Documentation
- [`AGENTS.md`](file:///c:/Users/chach/floodtail/AGENTS.md): Full specification of all 11 specialized agents, inputs, outputs, and halt conditions.
- [`EXPLAINABILITY.md`](file:///c:/Users/chach/floodtail/EXPLAINABILITY.md): The 7-step mathematical trace and decision explanation framework.
- [`METHODOLOGY.md`](file:///c:/Users/chach/floodtail/METHODOLOGY.md): Scientific documentation of Poisson event rates, Euler allocation, and CRN marginal TVaR.
- [`MODEL_CARD.md`](file:///c:/Users/chach/floodtail/MODEL_CARD.md): Formal model card covering intended use, inputs, outputs, and limitations.
- [`ASSUMPTIONS.md`](file:///c:/Users/chach/floodtail/ASSUMPTIONS.md): Comprehensive register of supplied, verified, benchmark, and prototype parameters.
- [`RISK_GOVERNANCE.md`](file:///c:/Users/chach/floodtail/RISK_GOVERNANCE.md): Underwriting guidelines, risk appetite thresholds, and compliance controls.
- [`DEPLOYMENT.md`](file:///c:/Users/chach/floodtail/DEPLOYMENT.md): Deployment instructions, operational modes, and offline presentation guidelines.
- [`DEMO_SCRIPT.md`](file:///c:/Users/chach/floodtail/DEMO_SCRIPT.md): 10-minute presentation guide, 5-minute live demo script, and Judge Q&A master defense.
- [`FINAL_VALIDATION_REPORT.md`](file:///c:/Users/chach/floodtail/FINAL_VALIDATION_REPORT.md): Quantitative verification and numerical reconciliation results.
