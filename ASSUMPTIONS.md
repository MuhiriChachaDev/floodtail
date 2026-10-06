# FLOODTAIL — Assumptions Register

This register documents all primary quantitative, geospatial, actuarial, and operational assumptions embedded in the FLOODTAIL demonstration platform.

| Assumption Name | Value / Specification | Status | Source / Baseline | Portfolio / Risk Impact |
|:---|:---|:---:|:---|:---|
| **Event Arrival Process** | Poisson distribution ($\lambda = \sum f_i$) | `VERIFIED` | Classical Catastrophe Modeling Standard | Dictates inter-arrival event independence across simulation years. |
| **Simulation Depth** | 10,000 Monte Carlo years | `VERIFIED` | Catastrophe Convergence Standard | Provides 40 empirical tail observations at $\alpha = 0.996$ (1-in-250 RP). |
| **Stochastic Random Seed** | `482913` | `VERIFIED` | Reproducibility Standard | Guarantees bit-identical loss realizations across repeated executions. |
| **Hazard Decay Function** | Radial Exponential Depth Decay | `PROTOTYPE` | Synthetic Engineering Formulation | Flood depth decreases smoothly from centroid outwards to perimeter. |
| **Flood Depth Cutoff** | $\ge 0.05$ meters | `BENCHMARK` | Flood Inundation Threshold | Filters negligible dampness to maintain computational sparsity. |
| **Depth-Damage Curves** | Piecewise linear monotonic curves | `BENCHMARK` | International FEMA / USACE Adaptation | Governs structural & contents damage percentage by property type. |
| **Construction Modifiers** | Concrete (0.85), Steel (1.00), Timber (1.15) | `BENCHMARK` | Structural Engineering Guidelines | Multiplies base depth-damage ratio based on construction vulnerability. |
| **Tail Confidence Level** | $\alpha = 0.996$ (1-in-250 years) | `SUPPLIED` | Solvency II / Actuarial Standard | Tail cutoff percentile for TVaR, PML, and capital allocation. |
| **Euler TVaR Allocation** | Fractional tail year loss attribution | `VERIFIED` | Actuarial Risk Allocation Theory | Ensures exact additive allocation: $\sum \text{Tail}_k = \text{Portfolio TVaR}$. |
| **Marginal TVaR Realization** | Common Random Numbers (CRN) | `VERIFIED` | Variance Reduction Actuarial Science | Evaluates true portfolio contribution using identical event set. |
| **Cost of Capital Rate ($r_{coc}$)** | $10.0\%$ per annum | `PROTOTYPE` | Reinsurance Pricing Waterfall Baseline | Charges capital cost on net tail exposure above expected loss. |
| **Underwriting Expense Ratio** | $10.0\%$ of technical premium | `PROTOTYPE` | Market Expense Ratio Baseline | Accounts for brokerage, operational, and administrative loadings. |
| **Policy Terms Application** | Deductibles & Limits per Policy | `VERIFIED` | Insurance Financial Mechanics | Ground-up loss clamped: $\text{Loss} = \min(\max(0, L_{gu} - D), Limit)$. |
| **Cryptographic Hash Chain** | SHA-256 with Genesis `00...00` | `VERIFIED` | Blockchain / Immutable Ledger Standard | Provides cryptographic guarantee against retroactive record tampering. |
| **Kenya Re Empirical Claims** | Historical claims loss settlement | `UNKNOWN` | Proprietary Reinsurer Data | Not incorporated in prototype; designated for Phase 7 production integration. |

---

### Status Definitions
- **SUPPLIED**: Explicitly defined by client, configuration, or statutory regulatory standards.
- **VERIFIED**: Empirically proven and verified by mathematical tests in the test suite.
- **BENCHMARK**: Accepted international engineering or scientific literature benchmark.
- **PROTOTYPE**: Configurable demonstration parameters representing realistic market operational baselines.
- **UNKNOWN**: External proprietary data not yet accessible to the prototype platform.
