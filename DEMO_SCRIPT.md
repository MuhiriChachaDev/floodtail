# FLOODTAIL — Championship Demo Script & Pitch Strategy

## 1. Ten-Minute Presentation Timing Breakdown

```
[0:00 - 0:45]  The Hook: "One Flood, One Portfolio, Correlated Catastrophe"
[0:45 - 1:30]  The Industry Problem: Why Standalone Underwriting Fails
[1:30 - 2:30]  The Solution: Agentic Reinsurance Decision Intelligence
[2:30 - 7:45]  Live Product Demonstration (5 minutes 15 seconds)
[7:45 - 8:45]  Business Value & Competitive Differentiation
[8:45 - 9:30]  Honest Disclosures & Scientific Limitations
[9:30 - 10:00] Closing Statement & Judge Q&A Transition
```

---

## 2. Pitch Hook & Opening Lines

> *"One flood does not create one insurance loss.*
> 
> *It turns hundreds of individually acceptable commercial policies into one devastating portfolio catastrophe.*
> 
> *Traditional underwriting looks at Policy A and Policy B as separate standalone buildings. FLOODTAIL makes the hidden portfolio correlation visible before the contract is signed."*

---

## 3. Championship Live Product Demo Script (5–6 Minutes)

### Step 1: Executive Overview (`01 — Overview`)
- **Action**: Open page. Point to top KPI row: Total TIV (KES 298.5M), Portfolio AAL (KES 42.9M), TVaR 99.6% (KES 237.1M).
- **Script**: *"We are viewing a 22-property commercial portfolio across Kenya simulated across 10,000 stochastic years. Notice that our baseline 1-in-250 year tail risk is KES 237M."*

### Step 2: Agent Control Centre (`04 — Agent Control`)
- **Action**: Show 11 specialized agents executing in sequential dependency order. Click on `TailRiskAgent` and `RiskAppetiteAgent`.
- **Script**: *"Under the hood, FLOODTAIL is governed by 11 typed, deterministic agents. There is no stochastic hallucination here. If data quality fails or loss tables fail reconciliation, critical agents halt execution immediately."*

### Step 3: Accumulation & Spatial Co-Hits (`06 — Accumulation`)
- **Action**: Highlight the Regional HHI (3,412) and Spatial Co-Hit Rate.
- **Script**: *"Here is where catastrophe risk hides. 42% of our exposure is clustered in Nairobi Industrial Area. When a 1-in-50 year riverine flood strikes, 8 separate policies are inundated simultaneously. That is spatial co-hit risk."*

### Step 4 & 5: The Killer Comparison (`09 — Policy Intelligence`)
- **Action**: Select **Policy A (POL_DEMO_A)** vs **Policy B (POL_DEMO_B)**.
- **Script**:
  - *"Look at this comparison. Policy A and Policy B have identical insured values: KES 25,000,000 each.*
  - *Their standalone flood depths look manageable. But look at their portfolio consequences:*
  - *Policy A adds **KES 27.96M** to the portfolio tail, while Policy B adds only **KES 18.96M**.*
  - *Why? Because Policy A sits in a dense accumulation cluster that co-occurs with our largest existing exposures."*

### Step 6: The "WHY?" Explainability Trace
- **Action**: Click the **WHY? Trace** on Policy A. Show the 7-step mathematical derivation card.
- **Script**: *"An underwriter cannot act on a black-box score. When the underwriter clicks 'WHY?', FLOODTAIL lays out the exact 7-step mathematical lineage from footprint depth (1.8m), to vulnerability damage ratio (42%), to ground-up loss, to Euler tail allocation, to marginal TVaR."*

### Step 7 & 8: Pricing Waterfall & Live What-If (`10 — Pricing`)
- **Action**: Show Technical Pricing Waterfall (Expected Loss KES 3.03M + Tail Charge KES 2.49M + Expense KES 552K = KES 6.07M Technical Premium). Drag the What-If Margin Slider.
- **Script**: *"We price the tail. Policy A requires a technical premium of KES 6.07M—more than double Policy B's KES 3.00M—purely because of its capital tail charge."*

### Step 9: Risk Appetite & Underwriting Governance (`12 — Risk Appetite`)
- **Action**: Show Policy A flagged as `REVIEW_REQUIRED` (Tail Share Breach: 11.8%).
- **Script**: *"The system deterministic rule engine evaluates appetite. Policy A breaches our 10% single-risk tail contribution cap, automatically escalating to senior review."*

### Step 10: Human Underwriter Decision (`13 — Decisions`)
- **Action**: Underwriter selects **MODIFY**. Attempts to submit without reason (validation error shows: reason required). Types reason: *"Surcharge KES 500,000 for floodwall mitigation warranty."* Submits successfully.
- **Script**: *"AI recommends; humans decide. If an underwriter modifies the price, FLOODTAIL mandates a justification reason before recording."*

### Step 11: Cryptographic Audit Trail (`14 — Audit`)
- **Action**: Click **Verify Cryptographic Chain**. Show Green Banner: `✓ Audit chain verified successfully (2 records).`
- **Script**: *"Every human decision is cryptographically SHA-256 hashed with its predecessor. No underwriter can retroactively alter a past decision without breaking the hash chain."*

---

## 4. Closing Statement

> *"FLOODTAIL does not use AI to replace the underwriter.*
> 
> *It uses agentic architecture to connect exposure, catastrophe risk, portfolio accumulation, tail risk, and technical pricing into one explainable workflow — so underwriters make evidence-backed decisions, and every decision remains permanently auditable.*
> 
> *FLOODTAIL turns catastrophe modeling into a governed reinsurance decision process."*

---

## 5. Master Judge Q&A Defense Guide

### Q1: Where is the AI? Why call it agentic?
**Answer**: *"FLOODTAIL utilizes a multi-agent decision architecture: 11 typed, specialized agents executing in dependency order. The agents are deterministic state-machines governed by strict actuarial contracts. We deliberately avoid generative LLMs for loss calculations because financial pricing and capital binding require auditable, non-stochastic mathematics. The intelligence lies in automated exposure validation, spatial hazard footprint intersection, Euler tail allocation, counterfactual Common Random Numbers, and automated governance packaging."*

### Q2: How is TVaR calculated, and how is tail risk allocated to policies?
**Answer**: *"Portfolio TVaR at $\alpha = 0.996$ is the expected loss given that annual aggregate loss exceeds the 99.6th percentile (the 1-in-250 year event). We allocate this tail risk to individual policies using Euler's allocation principle: each policy's tail contribution is the weighted average of its simulated losses during the portfolio's tail years. Because this satisfies Euler's homogeneous allocation theorem, the sum of policy tail contributions equals the portfolio TVaR exactly ($237,083,155.00 KES = 237,083,155.00 KES$)."*

### Q3: Why Common Random Numbers (CRN) for Marginal TVaR instead of Shapley / SHAP?
**Answer**: *"Shapley values require computing all $2^N$ portfolio permutations, which is computationally intractable for enterprise portfolios. Instead, we use Common Random Numbers (CRN): we compute the exact portfolio TVaR with and without policy $k$ holding the underlying 10,000-year stochastic event sequence constant. This isolates the true marginal variance reduction without introducing simulation noise."*

### Q4: Is this model calibrated to Kenya?
**Answer**: *"We are completely honest: FLOODTAIL is an enterprise prototype. The spatial event footprints represent realistic riverine inundation zones in Nairobi, Mombasa, and Kisumu, and the depth-damage curves adapt international engineering benchmarks (FEMA/USACE) with construction modifiers. However, it has not yet been fitted to Kenya Re's proprietary historical claims settlement data. Phase 7 is designed specifically to integrate proprietary Kenya loss history."*

### Q5: How do you prevent underwriters from abusing manual overrides?
**Answer**: *"Human-in-the-loop governance is enforced at the database level. An underwriter can ACCEPT, MODIFY, or REJECT. If MODIFY or REJECT is selected, the system programmatically rejects empty justifications. The decision, user ID, original technical price, modified price, and reason are hashed with the predecessor record in an append-only SHA-256 chain. Any retroactive modification breaks the hash chain immediately."*
