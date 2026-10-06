# FLOODTAIL

**AI-assisted flood catastrophe and reinsurance portfolio decision-intelligence system.**

---

## Purpose

FLOODTAIL is a professional tool for modelling flood catastrophe risk and
supporting reinsurance portfolio decisions. The eventual pipeline covers:

```
DATA → DATA QUALITY → EVENT SET → HAZARD → EXPOSURE → VULNERABILITY
→ LOSS → PORTFOLIO AGGREGATION → TAIL RISK → PRICING → SCENARIO
→ HUMAN DECISION → AUDIT
```

## Phase 1 Scope

Phase 1 establishes the **backend foundation** only:

- Python environment and dependency management
- Central configuration (YAML + Pydantic)
- Typed data contracts for every pipeline stage
- Run context for reproducibility
- Structured logging
- Custom exception hierarchy
- Application bootstrap
- Comprehensive foundation tests
- Git repository

Phase 1 does **not** include: database, frontend, catastrophe calculations,
ML models, maps, dashboards, or agents.

## Technology

| Component        | Technology                     |
| ---------------- | ------------------------------ |
| Language         | Python 3.14 (compatible ≥3.11)|
| Data contracts   | Pydantic v2                    |
| Configuration    | YAML + Pydantic                |
| Data processing  | pandas, NumPy (foundation)     |
| Testing          | pytest                         |
| Logging          | Python `logging` (structured)  |

## Environment Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Windows cmd)
.venv\Scripts\activate

# Activate (Unix/macOS)
source .venv/bin/activate
```

## Installation

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Running the Application

```bash
python app.py
```

Expected output:

```
FLOODTAIL
Version:          0.1.0
Environment:      development
Run ID:           <unique UUID>
Simulation years: 10000
Seed:             482913
System status:    READY FOR PHASE 2
```

## Running Tests

```bash
pytest
```

Or with verbose output:

```bash
pytest -v
```

## Project Structure

```
floodtail/
├── data/
│   ├── raw/            # Raw input data (not committed)
│   ├── processed/      # Cleaned / transformed data
│   └── demo/           # Synthetic demonstration data
├── src/
│   ├── __init__.py     # Package marker
│   ├── config.py       # Configuration loader + typed models
│   ├── schemas.py      # Pydantic data contracts
│   ├── exceptions.py   # Custom exception hierarchy
│   └── logging_config.py  # Structured logging setup
├── tests/
│   ├── __init__.py
│   └── test_foundation.py  # Phase 1 test suite
├── app.py              # Application entry point
├── config.yaml         # Central configuration
├── requirements.txt    # Python dependencies
├── README.md
└── .gitignore
```

## Configuration

Configuration lives in `config.yaml` with these sections:

| Section      | Purpose                                   |
| ------------ | ----------------------------------------- |
| `project`    | Name, version, environment                |
| `simulation` | Monte-Carlo years, random seed            |
| `risk`       | Tail confidence level                     |
| `pricing`    | Cost of capital, expense rate             |
| `model`      | Hazard/vulnerability/model version IDs    |
| `governance` | Human decision and audit flags            |
| `data`       | Required portfolio fields                 |

> **Note:** The current prototype configuration is **not** Kenya-specific
> calibration, production pricing, or regulatory approval. All values are
> placeholders for development and testing.

## Data Contracts

Every pipeline stage communicates through typed Pydantic schemas:

| Schema               | Pipeline Stage        |
| -------------------- | --------------------- |
| `PortfolioRecord`    | Exposure data         |
| `EventRecord`        | Event set             |
| `HazardResult`       | Hazard model output   |
| `VulnerabilityResult`| Vulnerability output  |
| `LossResult`         | Loss calculation      |
| `AnnualLossResult`   | Year-loss table       |
| `PolicyTailResult`   | Tail-risk allocation  |
| `PricingResult`      | Technical pricing     |
| `RunContext`         | Reproducibility       |
| `AgentResult`        | Agent result envelope |

## Current Status

```
╔══════════════════════════════════════════╗
║  CURRENT STATUS:                         ║
║  PHASE 1 — BACKEND FOUNDATION            ║
║  System status: READY FOR PHASE 2        ║
╚══════════════════════════════════════════╝
```

**Next phase:** Database + Portfolio Ingestion + Data Quality

---

*FLOODTAIL — Built for catastrophe intelligence.*
