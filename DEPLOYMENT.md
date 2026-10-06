# FLOODTAIL — Deployment & Operation Manual

## System Requirements
- **Operating System**: Windows 10/11, macOS (Apple Silicon / Intel), or Linux (Ubuntu 22.04 LTS+)
- **Python Runtime**: Python 3.10 to 3.14 (Verified in development on Python 3.14.5)
- **RAM**: 4 GB minimum (8 GB recommended for 10,000-year simulations)
- **Disk Space**: ~500 MB for repository, dependencies, and demo artifacts
- **Network**: Completely self-contained / zero-cloud dependency; operates 100% offline.

---

## 1. Quick Start Installation

```bash
# 1. Clone repository
git clone https://github.com/MuhiriChachaDev/floodtail.git
cd floodtail

# 2. Create and activate virtual environment
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. Running FLOODTAIL

### A. Web Application (Streamlit GUI)
Launch the full interactive enterprise reinsurance platform:

```bash
streamlit run app.py
```
- The browser will automatically open to `http://localhost:8501`.
- In the sidebar, click **🎯 Demo** to immediately execute and load the frozen 10,000-year demonstration pipeline.

### B. Headless CLI Bootstrap & Smoke Test
To verify database, configuration, and environment integrity headlessly:

```bash
python app.py
```
Output:
```
FLOODTAIL backend bootstrap complete. Run ID: <UUID>
```

### C. Automated Test Suite Execution
Execute the entire regression and validation suite:

```bash
pytest -v
```
All 128 tests across foundation, data layer, catastrophe engine, risk analytics, agent workflow, and frontend smoke will execute and pass.

---

## 3. Operational Modes

### 🎯 Demo Mode (Frozen Championship Data)
- **Pre-configured Dataset**: 22 diverse commercial and residential policies across Nairobi, Mombasa, and Kisumu (`data/demo/portfolio_ab_demo.csv`).
- **Pre-configured Hazard & Events**: 80,161 loss occurrences across 10,000 simulated years.
- **Speed**: Executes in ~25 seconds on first run, cached in session state for instant sub-second page transitions.
- **Purpose**: High-reliability presentations, judge demonstrations, and stakeholder rehearsals.

### 📡 Live Mode (Custom Ingestion)
- Underwriters can upload raw custom portfolios (CSV / Parquet).
- Automatic schema mapping and validation via `SchemaMapper`.
- 11-rule data quality audit and automated coordinate swapping detection via `DataQualityAuditor`.
- Dynamic catastrophe simulation and risk calculation on user-provided assets.

---

## 4. Offline Fallback & Championship Defense Plan
If presentation venue WiFi fails, external networks drop, or cloud services disconnect:
1. FLOODTAIL requires **zero internet access**. All geospatial mathematics, Plotly charts, SQLite databases, and agent pipelines run locally on `localhost`.
2. A backup copy of the repository and demo databases is archived locally in `data/demo/`.
3. If port 8501 is busy:
   ```bash
   streamlit run app.py --server.port=8502
   ```

---

## 5. Troubleshooting Guide

| Issue | Root Cause | Resolution |
|:---|:---|:---|
| `No module named 'streamlit'` | Virtual environment not activated | Run `.venv\Scripts\Activate.ps1` (or `source .venv/bin/activate`). |
| `missing ScriptRunContext` | Running Streamlit code inside bare Python | Safe to ignore; headless CLI mode detects bare execution via `st.runtime.exists()`. |
| Port 8501 already in use | Another background process running | Use `streamlit run app.py --server.port=8502`. |
| SQLite `database locked` | Concurrent process accessing SQLite DB | Ensure background test tasks are terminated. |
