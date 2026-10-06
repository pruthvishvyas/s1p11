# 📈 D2C Weekly Growth & Profit Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Gradio](https://img.shields.io/badge/Gradio-App-orange.svg)](https://gradio.app/)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://reactjs.org/)
[![Cloudflare Pages](https://img.shields.io/badge/Cloudflare-Pages-f38020.svg)](https://pages.cloudflare.com/)
[![MCP Server](https://img.shields.io/badge/Claude-MCP%20Server-7C3AED.svg)](https://modelcontextprotocol.io/)

A complete, end-to-end financial intelligence and growth analytics suite built for Direct-to-Consumer (D2C) brands. This repository contains both a **Python Data Engineering & ML Modeling Engine** (with Gradio dashboard) and a **React + Cloudflare Edge Dashboard** (with Model Context Protocol / MCP integration for AI Assistants like Claude).

---

## 🌟 Executive Overview

Maintaining sustainable e-commerce growth requires tracking unit economics, cash runways, marketing channel ROAS, and promotional margins simultaneously. This platform analyzes weekly store performance data, detects anomalies, forecasts multi-week loss risk using Machine Learning, and presents key insights for decision-makers.

### Core Capabilities

- **📊 Trailing 13-Week KPI Tracking**: Monitor Net Revenue, Net Profit, Margin %, ROAS, CAC, LTV:CAC ratio, Cash Runway (weeks), and Loss Week rates.
- **🤖 Predictive ML Engine & Risk Modeling**: `GradientBoostingClassifier` trained on historical promo rates, discount depth, and multi-week spend lag series to forecast loss-week risk.
- **📈 Interactive Gradio Executive App**: Multi-tab Python interactive portal featuring dynamic Plotly visualizations, priority week rankings, domain intel tables, visual report gallery, and live scenario forecasting.
- **⚡ React + Cloudflare Edge Dashboard**: High-speed, responsive frontend hosted on Cloudflare Pages with edge-computed forecasting (`d2c_weekly_growth/`).
- **🧠 Claude Model Context Protocol (MCP) Server**: Allows AI agents (Claude Desktop, VS Code, Cursor) to directly connect and query live KPIs, projections, and recommendations in natural language.
- **📑 Automated Executive Boardroom Reports**: Generates full PPT-styled textual briefs and key diagnostic charts (`reports/*.png`).

---

## 🏗️ Architecture & Project Structure

```
content/s1p11/
├── config/
│   └── config.py               # Master configuration, threshold functions, & column mappings
├── src/                        # Python Analytics & Machine Learning Pipeline
│   ├── data/                   # Ingestion & Data Cleaning modules
│   ├── features/               # Feature engineering (lags, ratios, rolling means)
│   ├── analytics/              # EDA, Business logic, KPI computations, and Insights generator
│   ├── models/                 # ML Models (Segmentation, Classification, Forecasting)
│   └── reporting/              # Chart generation & PowerPoint export utilities
├── data/
│   ├── raw/                    # Input e-commerce datasets
│   └── processed/              # Processed feature store CSVs
├── models/                     # Saved ML model artifacts (.pkl files)
├── output/                     # Generated JSON analytical contracts & dashboard payloads
├── reports/                    # Generated chart PNG gallery & executive summary documents
├── main.py                     # CLI Pipeline Orchestrator (Runs all 10 analytics phases)
├── app.py                      # Interactive Gradio Dashboard & ML Forecaster
├── frontend_contract.json      # Frontend-backend JSON specification schema
│
└── d2c_weekly_growth/          # React + Cloudflare Edge Application
    ├── public/data/            # Dashboard static JSON data endpoints
    ├── src/                    # React components, pages, and context providers
    ├── worker/                 # Cloudflare Worker script (Serving web app & /mcp endpoint)
    └── wrangler.toml           # Cloudflare deployment settings
```

---

## 🚀 Quick Start Guide

### Prerequisites

- **Python 3.9+** (For the Data Pipeline & Gradio App)
- **Node.js 18+** & `npm` (For the React / Cloudflare Dashboard)

---

### 1. Python Data Pipeline & Gradio App Setup

1. **Install Dependencies**:
   ```bash
   pip install pandas numpy scikit-learn gradio plotly joblib python-pptx
   ```

2. **Execute the End-to-End Pipeline**:
   Run the 10-phase pipeline orchestrator (Ingest ➔ Clean ➔ Feature Engineering ➔ EDA ➔ Segmentation ➔ Classification ➔ Business Logic ➔ Insights ➔ Export):
   ```bash
   python main.py
   ```

3. **Launch the Gradio Dashboard**:
   ```bash
   python app.py
   ```
   Open `http://localhost:7860` in your web browser to explore KPIs, risk models, visual gallery, and scenario planner.

---

### 2. React + Cloudflare Edge Dashboard Setup

1. **Navigate to Frontend Directory**:
   ```bash
   cd d2c_weekly_growth
   ```

2. **Install Node Dependencies**:
   ```bash
   npm install
   ```

3. **Start Local Development Server**:
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173` to view the modern web app interface.

---

## 🤖 Claude Model Context Protocol (MCP) Setup

The Cloudflare Worker in `d2c_weekly_growth/worker/forecaster.js` exposes an MCP endpoint at `/mcp` (or `/sse`), enabling AI assistants like Claude Desktop, Cursor, or VS Code to query dashboard metrics natively.

### Connecting Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "d2c-growth-analytics": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-fetch",
        "https://<your-cloudflare-worker-domain>/mcp"
      ]
    }
  }
}
```

### Available MCP Agent Tools

- `get_d2c_summary`: Returns high-level business overview, target thresholds, and status.
- `get_kpis`: Returns latest trailing 13-week metrics (Revenue, Margin, ROAS, CAC, Runway).
- `run_forecast`: Executes multi-week revenue and net profit predictions.

---

## ☁️ Cloudflare Pages & Worker Deployment

To deploy the React dashboard and Worker endpoint to Cloudflare:

```bash
cd d2c_weekly_growth
npm run build
npm run deploy
```

Set the forecast lookup secret via Wrangler:
```bash
npx wrangler secret put FORECAST_LOOKUP
```

---

## 📊 Analytics & Insights Schema

The platform generates standard contract JSON payloads stored in `output/`:
- `output/understand/kpis.json`: Core financial metrics and 13-week comparison.
- `output/understand/anomalies.json`: Isolation Forest detected performance anomalies.
- `output/decide/insights.json`: Structured findings with severity, evidence, and recommended actions.
- `output/decide/simulations/`: Channel spend and promo depth scenario modeling outputs.

---

## 📄 License

Private & Proprietary. Created for D2C Weekly Growth & Profit Management.
