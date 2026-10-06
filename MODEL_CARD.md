# FLOODTAIL — Model Card & Risk Governance Specification

## Model Details
- **Model Name**: FLOODTAIL Reinsurance Catastrophe & Portfolio Decision Engine
- **Release Version**: `v1.0.0-demo`
- **Release Date**: October 2026
- **Model Type**: Multi-tier stochastic catastrophe simulation, marginal tail risk allocation, technical pricing waterfall, and deterministic multi-agent governance pipeline.
- **Maintainers**: FLOODTAIL Engineering & Quantitative Catastrophe Modeling Team

---

## Intended Use
- **Primary Use**: Demonstration of portfolio-aware reinsurance catastrophe risk intelligence, policy tail risk attribution, marginal TVaR evaluation, and explainable human-in-the-loop underwriting decision governance.
- **Intended Users**: Reinsurance treaty & facultative underwriters, catastrophe risk analysts, actuarial teams, risk governance officers.
- **Operational Mode**: Pre-underwriting risk screening, capital allocation evaluation, portfolio accumulation monitoring, counterfactual what-if sensitivity analysis, and auditable decision logging.

## Out-of-Scope / Not Intended Use
- ❌ **Direct Commercial Underwriting Execution**: FLOODTAIL is a prototype demonstration engine. It is not approved for binding production legal contracts without empirical Kenya claims calibration and regulatory clearance.
- ❌ **Automated Dark Underwriting**: Autonomous policy acceptance without certified underwriter review is strictly disallowed by system architecture.
- ❌ **Black Box Financial Predictions**: Black-box generative neural networks are not permitted to infer loss amounts or bind capital.

---

## Inputs and Data Contracts
| Input | Type | Source / Format | Validation Rule |
|:---|:---|:---|:---|
| **Exposure Portfolio** | Tabular | CSV / Parquet | Valid coordinates (Lat/Lon within bounds), positive TIV, typed property type & construction class |
| **Event Catalogue** | Tabular | CSV (`events.csv`) | Poisson annual frequencies $\ge 0$, severity scale $\ge 0$, valid footprint reference |
| **Hazard Footprints** | Geospatial / GeoJSON | JSON (`footprints.json`) | Physical footprint centroids, decay radius, positive flood depth |
| **Vulnerability Curves** | Piecewise linear | In-memory / Config | Monotonic damage ratios $\in [0, 1]$, depth non-negative |
| **Simulation Parameters** | YAML Config | `config.yaml` | Simulation years ($N \ge 1$), seed, tail confidence $\alpha \in (0, 1)$ |

---

## Outputs and Metrics
- **AAL (Average Annual Loss)**: Expected annual loss across all simulated Monte Carlo years.
- **OEP / AEP Curves**: Occurrence Exceedance Probability and Aggregate Exceedance Probability curves across 10-year to 500-year return periods.
- **VaR / TVaR ($\alpha = 0.996$)**: Value at Risk and Tail Value at Risk at the 1-in-250 year return period.
- **Euler Policy Tail Allocation**: Additive policy tail risk attribution reconciling exactly to portfolio TVaR.
- **CRN Marginal TVaR**: Non-additive marginal impact evaluated via Common Random Numbers ($TVaR(\mathcal{P}) - TVaR(\mathcal{P} \setminus \{k\})$).
- **Technical Pricing Waterfall**: Expected Loss + Cost of Capital Tail Charge + Expense Loading.
- **Cryptographic Audit Trail**: Immutable SHA-256 hash-chained decision records in SQLite.

---

## Modeling Limitations & Scientific Disclosures
1. **Prototype Hazard Representation**: Synthetic flood extent footprints utilize radial exponential decay and benchmark flood footprints rather than 2D hydrodynamic Saint-Venant hydraulic simulations.
2. **Benchmark Vulnerability Curves**: Depth-damage relationships utilize international engineering benchmark curves (FEMA/USACE prototype equivalents) adjusted with construction modifiers, rather than empirical Kenya claims loss histories.
3. **Absence of Kenya Claims Calibration**: Losses are estimated for portfolio comparison and demonstration; historical loss settlement data from Kenya Re has not been fitted to the damage functions.
4. **Sample Support at Tail**: At $\alpha = 0.996$, a 10,000-year simulation provides 40 tail observations; a 1,000-year run provides only 4 tail observations. The sample depth is visibly disclosed in the UI.

---

## Ethical & Governance Principles
- **Explainability**: Every underwriting recommendation provides a deterministic 7-step mathematical trace and key risk factor breakdown.
- **Human Primacy**: AI agents recommend; certified human underwriters decide. Any modification or rejection of technical pricing mandates an auditable rationale.
- **Tamper Evidence**: All decisions are hashed with their predecessor in an append-only cryptographic ledger.
