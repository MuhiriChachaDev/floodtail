# FLOODTAIL — Backend Architecture & Workflow

**Product job:** Help a reinsurance **underwriter** understand flood risk for **whatever portfolio they ingest** (Nairobi today, other places tomorrow), see grounded loss / capital numbers, and get a **simple actionable insight** — e.g. how many insured houses are in play and how much to set apart without under- or over-budgeting.

**AI posture:** **Agentic-first** (LangGraph + LangChain) + **predictive ML**. Agents orchestrate analysis and may **present money numbers**, but only numbers produced by real pipeline analysis — never guessed or invented by the LLM.

---

## 0. Who · what · why (one screen)

```mermaid
flowchart LR
    UW["Underwriter"]
    Need["Needs to know<br/>• Where is risk concentrated?<br/>• How many insured assets?<br/>• What loss / capital to set aside?<br/>• What to do next?"]
    Sys["FLOODTAIL backend"]
    Out["Grounded metrics<br/>+ actionable insight"]

    UW --> Need --> Sys --> Out --> UW
```

| Question the underwriter asks | What the system answers |
|-------------------------------|-------------------------|
| What did I upload? | Location-agnostic portfolio from **ingested data** (count, TIV, classes, bbox) |
| How bad can flood losses get? | EP / RP losses from **analysis pipeline** (ML + financial math) |
| How much should I set apart? | Recommended capital / budget band — **not under, not over** — derived from EP/AAL + appetite rules |
| What should I do? | Short actionable insight: `ACCEPT` / `REVIEW` / `ESCALATE` + next step |

---

## 1. System context (flexible geography)

```mermaid
flowchart TB
    UW["Underwriter / API client"]

    subgraph API["apps/api — FastAPI"]
        MW["Auth · RBAC · Tenant"]
        R["Routers<br/>portfolios · ingest · runs · models<br/>insight · query · audit · health"]
        Store["Portfolio / Run store"]
    end

    subgraph AgentRuntime["AGENTIC CORE — LangGraph + LangChain"]
        Graph["State machine graph"]
        Tools["LangChain tools<br/>schema · geo · ML invoke · EP · insight · audit"]
        LLM["Ollama LLM<br/>presents analysis · never invents figures"]
    end

    subgraph Predictive["PREDICTIVE ML"]
        Feat["Feature builder<br/>from ingested columns + enrichments"]
        Haz["HazardModel"]
        Vuln["VulnerabilityModel"]
        Reg["Model registry + SHA-256"]
    end

    subgraph GroundedMath["GROUNDED ANALYSIS MATH<br/>thin · auditable · no LLM invent"]
        Depth["score → depth"]
        Loss["damage × TIV"]
        EP["EP / AAL / capital band"]
        Acc["Accumulation by class / hotspot / region"]
    end

    Data["Ingested data<br/>any location CSV / layers<br/>+ optional built-in Nairobi starter"]
    Models["models/ versioned artifacts"]
    Ollama["Ollama"]

    UW --> MW --> R --> Graph
    Graph --> Tools
    Tools --> LLM
    Tools --> Feat
    Tools --> Haz
    Tools --> Vuln
    Tools --> Depth
    Tools --> Loss
    Tools --> EP
    Tools --> Acc
    Feat --> Data
    Haz --> Reg
    Vuln --> Reg
    Reg --> Models
    LLM --> Ollama
    R --> Store
```

**Flexibility rule:** no Nairobi-only business logic in code paths. Location, housing classes, RP profile, and enrichment layers come from **what was ingested** + a **run assumptions profile**. Nairobi is a starter dataset, not the product boundary.

---

## 2. Authority: who may say money numbers

```mermaid
flowchart TD
    Q["Can this number appear in a briefing / insight?"]
    Q --> A{"Was it produced by<br/>grounded analysis<br/>this run?"}
    A -->|Yes — in allowlist| OK["LLM / agent MAY present it<br/>cite source · include in insight"]
    A -->|No — LLM guessed| Block["REJECT<br/>template fallback + audit event"]
```

| Source | Examples | LLM may present? |
|--------|----------|------------------|
| Ingest stats | `# insured houses`, total TIV, class mix | Yes |
| ML outputs | predicted hazard scores, damage ratios | Yes (as model outputs) |
| Grounded math | tier losses, EP points, AAL, **capital set-aside band** | Yes — **only after computed** |
| LLM free imagination | “loss is 50M because I think so” | **Never** |

Agents do **real analysis** (tools call ML + math). The LLM **narrates and recommends** using those tool results. That is “agentic analysis,” not guessing.

---

## 3. LangGraph pipeline (location-flexible)

Critical stages halt on `FAILED`. Insight stage is required for underwriter value but can degrade to a deterministic template if Ollama is down (numbers still from allowlist).

```mermaid
flowchart TD
    Start([POST /v1/runs<br/>or ingest → run]) --> S0

    S0["0 · Ingest & SchemaMap<br/>LangChain tools · CRITICAL<br/>any location · map columns · stamp provenance"]
    S1["1 · DQ / PII / Geocode / Enrich<br/>Agentic + rules · CRITICAL"]
    S2["2 · FreeTextExposure optional<br/>Agentic · non-critical"]
    S3["3 · HumanGate_1<br/>approve features / exposure"]
    S4["4 · PredictHazard<br/>ML · CRITICAL"]
    S5["5 · PredictVulnerability<br/>ML · CRITICAL"]
    S6["6 · Grounded Financial + EP + Capital band<br/>math tools · CRITICAL"]
    S7["7 · XAI<br/>SHAP / CF · non-critical"]
    S8["8 · Actionable Insight Agent<br/>LangGraph · underwriter package"]
    S9["9 · Governance / Audit / HumanGate_2"]

    S0 -->|ok| S1
    S0 -->|schema fatal| Halt([FAILED])
    S1 -->|ok| S2
    S1 -->|FAILED| Halt
    S2 --> S3
    S3 -->|approved / gate off| S4
    S3 -->|rejected| Halt
    S4 -->|ok| S5
    S4 -->|model / hash fail| Halt
    S5 -->|ok| S6
    S5 -->|model / hash fail| Halt
    S6 -->|ok| S7
    S6 -->|reconcile fail| Halt
    S7 --> S8
    S8 --> S9
    S9 --> Done([Insight ready for underwriter])

    style S0 fill:#6cf,stroke:#333
    style S1 fill:#f96,stroke:#333
    style S4 fill:#f96,stroke:#333
    style S5 fill:#f96,stroke:#333
    style S6 fill:#f96,stroke:#333
    style S8 fill:#3a3,color:#fff,stroke:#333
    style Halt fill:#c33,color:#fff
    style Done fill:#3a3,color:#fff
```

---

## 4. Underwriter actionable insight (core product output)

For a specific ingested location / portfolio (example: Nairobi), the insight package must answer:

```mermaid
flowchart LR
    subgraph Facts["GROUNDED FACTS"]
        N["Insured houses / locations<br/>count from ingest"]
        TIV["Total insured value TIV"]
        Conc["Concentration<br/>class · hotspot · region"]
        EP["EP / RP losses + AAL"]
    end

    subgraph Capital["SET-ASIDE GUIDANCE"]
        Low["Floor — avoid under-budgeting<br/>e.g. linked to higher RP / PML"]
        Mid["Central — AAL / technical view"]
        High["Ceiling — avoid over-budgeting<br/>appetite / capital policy caps"]
        Band["Recommended capital / budget band"]
    end

    subgraph Action["ACTION"]
        Rec["ACCEPT / REVIEW / ESCALATE"]
        Next["1–3 concrete next steps"]
    end

    Facts --> Capital --> Band --> Action
```

### Example insight shape (illustrative)

```text
Location / book: Nairobi County (from ingest)
Insured houses: 600
Total TIV: KES X

Recommended set-aside (this run):
  · Do not go below: KES L  (under-budget risk — e.g. RP100 / agreed PML proxy)
  · Central view:     KES C  (discrete AAL / technical)
  · Do not exceed:    KES H  (over-budget / appetite ceiling)

Recommendation: REVIEW
Why:
  · Informal housing share drives Y% of tier loss
  · Hotspot overlap: N named areas
Next:
  · Cap new writings in top hotspot cluster
  · Re-run after actuary checks vuln model pin
```

All KES figures in that package come from **tool outputs** (ingest + EP/capital tools), then the Insight Agent writes the prose.

---

## 5. Grounded analysis math (thin, auditable)

Still required so capital guidance is reproducible. Not “the product brain” — a **tool** the agents call.

```mermaid
flowchart LR
    Exp["Ingested exposure<br/>loc · class · tiv<br/>hazard features if present"]
    Depth["depth = score × D_max<br/>D_max from assumptions profile"]
    DR["damage_ratio<br/>ML or prior curves"]
    Loss["loss = DR × tiv"]
    EP["EP points + AAL"]
    Cap["Capital / set-aside band<br/>floor · central · ceiling"]

    Exp --> Depth --> DR --> Loss --> EP --> Cap
```

| Concept | Meaning for underwriter |
|---------|-------------------------|
| Floor | Amount below which you are **under-budgeting** severe risk |
| Central | Expected / technical view (e.g. discrete AAL) |
| Ceiling | Amount above which you are likely **over-budgeting** vs appetite |

Exact band formula lives in config/assumptions (not hardcoded per city).

---

## 6. Ingest → any location

```mermaid
flowchart TD
    Up["Underwriter uploads<br/>CSV ± hotspot/hazard layers"]
    Map["SchemaMap agent<br/>LangChain · map columns<br/>lat lon tiv class …"]
    Prov["Provenance<br/>synthetic? source? location label"]
    DQ["DQ<br/>bbox from data or profile<br/>TIV>0 · class in allowed set"]
    Store["Portfolio stored<br/>location = derived from data"]
    Run["Run uses THIS ingest only"]

    Up --> Map --> Prov --> DQ --> Store --> Run
```

| Flexible input | Bound how? |
|----------------|------------|
| Geography | From uploaded coords / optional bbox in assumptions |
| Housing / occupancy classes | From data + configurable enum / mapper |
| Hazard | Uploaded scores, rasters, or ML features from enrichment |
| RP / D_max / capital policy | Assumptions profile on the run |
| Starter Nairobi kit | One built-in ingest option — not a code special-case forever |

---

## 7. API workflows

### 7a. Ingest → run → insight

```mermaid
sequenceDiagram
    participant U as Underwriter
    participant API as FastAPI
    participant G as LangGraph
    participant ML as ML tools
    participant Math as EP / capital tools
    participant LLM as Ollama

    U->>API: POST /v1/portfolios (upload any location)
    API->>G: SchemaMap + DQ + PII
    G-->>API: portfolio_id · ingest stats
    API-->>U: portfolio_id · #houses · TIV

    U->>API: POST /v1/runs
    API->>G: start graph
    G->>ML: predict hazard + vulnerability
    G->>Math: losses · EP · capital band
    G->>LLM: Insight Agent (allowlisted numbers only)
    LLM-->>G: actionable insight prose
    G-->>API: metrics + insight package
    API-->>U: run_id

    U->>API: GET /v1/runs/{id}/insight
    API-->>U: houses · set-aside band · ACCEPT/REVIEW/ESCALATE · next steps
```

### 7b. Number discipline inside the Insight Agent

```mermaid
flowchart TD
    Tools["Tools return allowlist<br/>houses, TIV, EP, AAL, band L/C/H"]
    Prompt["LLM prompt<br/>frozen allowlist in context"]
    Draft["Draft insight"]
    Val["output_validation<br/>every money token ∈ allowlist"]
    OK["Return insight"]
    Bad["Reject draft → template insight<br/>same numbers · audit event"]

    Tools --> Prompt --> Draft --> Val
    Val -->|pass| OK
    Val -->|fail| Bad
```

---

## 8. Failure & degrade

```mermaid
flowchart TD
    Ev["Stage outcome"]
    Ev -->|CRITICAL FAILED| Halt["Halt run"]
    Ev -->|Ollama down| Tmpl["Template insight<br/>numbers still from tools"]
    Ev -->|LLM invents KES| Reject["Validator reject<br/>template + audit"]
    Ev -->|Empty / bad ingest| FailDQ["FAILED at SchemaMap / DQ"]
```

---

## 9. Backend build phases (updated)

```mermaid
flowchart LR
    B1["B1 · Flexible ingest<br/>+ grounded EP/capital tools<br/>+ metrics API"]
    B2["B2 · ML hazard/vuln<br/>location-agnostic features"]
    B3["B3 · LangGraph/LangChain<br/>Insight Agent + briefing/query"]
    B4["B4 · Security · RBAC · audit"]

    B1 --> B2 --> B3 --> B4
```

| Phase | Delivers for underwriter |
|-------|--------------------------|
| B1 | Upload book → see #houses, TIV, EP, **set-aside band** |
| B2 | ML changes predictions → losses/band move; delta visible |
| B3 | Natural-language **actionable insight** grounded in tool numbers |
| B4 | Roles, prompt defence, hash-chained decisions |

---

## 10. API surface (insight-centric)

```mermaid
flowchart LR
    subgraph v1["/v1"]
        H["GET /health"]
        P["POST/GET /portfolios"]
        M["POST/GET /models"]
        R["POST/GET /runs"]
        Rm["GET /runs/{id}/metrics"]
        Ri["GET /runs/{id}/insight"]
        Rp["GET /runs/{id}/properties"]
        Ra["GET /runs/{id}/accumulation"]
        Re["GET /runs/{id}/explanations/*"]
        Rn["GET /runs/{id}/narrative"]
        Rq["POST /runs/{id}/query"]
        Rap["POST /runs/{id}/approve"]
        Au["GET /audit"]
    end

    Ri --> Insight["houses · TIV · set-aside band<br/>recommendation · next steps"]
    Rm --> Metrics["EP · AAL · labels · model versions"]
```

---

## 11. Do we understand the product? (checklist)

| Intent | Captured? |
|--------|-----------|
| Underwriter is the primary user | Yes |
| Works for **different locations** based on **ingested data** | Yes |
| Not Nairobi-hardcoded forever | Yes — starter data only |
| More **ML + LangGraph/LangChain agentic** than brittle rules | Yes |
| LLM **can show money numbers** from **real agentic analysis** | Yes — tools first, then present |
| LLM must **not guess** money | Yes — allowlist validator |
| Simple **actionable** output | Yes — insight package |
| For a place (e.g. Nairobi): **# insured houses** + **amount to set apart** without under/over budgeting | Yes — count + capital band L/C/H |

---

*Nairobi starter kit remains the default demo ingest. Product boundary = whatever valid portfolio the underwriter uploads.*
