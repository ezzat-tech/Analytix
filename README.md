# Data Analyst Agent

An orchestrated multi-agent data analysis assistant that keeps raw data on your machine while AI Models either local through ollama or cloud-based such as OpenAI, Claude or Ollama Cloud answer your natural-language questions about your datasets.

## Overview

The system combines a state-machine orchestrator, specialized analysis agents, and an AI Model-driven code-generation loop. The AI Models ("brain") only receives metadata (column names, data types) plus small query results, while the Python runtime ("hands") executes the heavy computations against the full dataset. This architecture scales to millions of rows (bounded by RAM) without exposing bulk data to external providers.

## Key Features

- Multi-agent pipeline (Ingestion, Exploration, Analysis, Transformation, Visualization, Reporting) coordinated by an async state machine.
- QueryEngine that turns plain-English prompts into executable Python, with automatic error classification and retry logic.
- Pluggable LLM backends (Ollama local, Ollama Cloud, OpenAI, Claude) configurable through the web settings panel or directly in configuration files.
- FastAPI backend consumed by a React + Vite dashboard.
- Persistent sessions, logs, and visualization artifacts stored on disk for auditability and reuse.

## Architecture Highlights

- **State Machine Orchestrator:** `src/orchestrator/state_machine.py` drives agent transitions, guards, and persistence.
- **Session Context:** `src/shared` holds session IDs, cached dataframes, profiling outputs, and accumulated messages.
- **Agent Registry:** Each agent in `src/agents` inherits from `BaseAgent`, executes LLM-authored code, and returns structured `AgentResult`s.
- **API Layer:** `src/api/server.py` exposes session management, uploads, query execution, and LLM configuration endpoints consumed by the frontend.
- **Frontend:** `frontend/` (React, TypeScript, vanilla CSS, Zustand) visualizes chat history, dataset previews, generated charts, and run logs.

See `docs/multi-agent-architecture.md` for the full flow diagram and state descriptions.

## Data Privacy Model

- **Local by default:** Bulk CSV/Excel/JSON/Parquet data stays in memory on your machine; only schemas, prompts, and targeted results are sent to the LLM.
- **Potential leakage:** Column names may reveal sensitive categories, and query results can surface individual values if requested explicitly.
- **Air-gapped option:** Use Ollama's local free models in the LLM configuration if your hardware is capable to keep all prompts, schemas, and results on-device for 100% local execution and complete security and privacy.

## Repository Layout

| Path | Description |
| --- | --- |
| `src/` | Python implementation (agents, orchestrator, API, LLM clients). |
| `src/agents/` | Specialized agents and skills for ingestion, analysis, visualization, reporting, transformation. |
| `src/api/` | FastAPI server, serializers, and session registry. |
| `src/config/` | Pydantic settings and logging configuration. |
| `src/llm/` | LLM configuration management, menu, and client wrappers. |
| `src/orchestrator/` | State machine and orchestration primitives. |
| `src/query/` | QueryEngine translating natural language into Python execution. |
| `src/main.py` | Core `Orchestrator` class coordinating specialized agents via state machine. |
| `frontend/` | React + Vite dashboard project (source, build artifacts, dependencies). |
| `config/` | Active LLM configuration and credentials YAML (plus templates). |
| `data/` | Persisted user-uploaded datasets and working CSV/Parquet files. |
| `docs/` | Reference documentation (e.g., multi-agent architecture notes). |
| `logs/` | Runtime log files such as `orchestrator.log`. |
| `outputs/` | Generated visualization files and other artifacts served to the UI. |
| `state/` | Saved session bundles and orchestrator state snapshots. |
| `requirements.txt` | Python dependencies. |
| `system explanations.md` | Capacity, privacy, and positioning notes. |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+ (for the React UI)
- Optional: [Ollama](https://ollama.ai) to run local models

### Backend Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### Run the FastAPI Server

```bash
uvicorn src.api.server:app --reload
```

- Serves REST endpoints on `http://localhost:8000`.
- Static charts appear under `/static`.
- Session JSON and outputs are persisted in `state/` and `outputs/`.

### Run the React Frontend

```bash
cd frontend
npm install
npm run dev
```

- Set `VITE_API_BASE_URL` in `frontend/.env.local` if the API is not on the default `http://localhost:8000`.
- 💡 **Configuration Note:** Once the dashboard is open in your browser, click the Settings panel icon in the sidebar to configure your LLM backend (Ollama, OpenAI, or Claude) and supply your API credentials.

## Workflow at a Glance

1. Ingestion Agent loads CSV, Excel, JSON, Parquet and profiles schemas.
2. Exploration Agent builds descriptive stats and data health checks.
3. Analysis Agent runs aggregations, regressions, correlations, etc.
4. Transformation Agent applies cleaning and feature engineering.
5. Visualization Agent creates charts saved to `outputs/`.
6. Reporting Agent stitches findings into narrative insights.

The state machine manages retries, error classification, and transitions; results flow back through the QueryEngine to the user.

## Session Artifacts

- `logs/orchestrator.log` – execution trace.
- `outputs/` – generated plots/tables (served to the UI).
- `state/*.json` – persisted session contexts and chat history.
- `data/` – uploaded datasets (auto-saved).

## Documentation & References

- `docs/multi-agent-architecture.md` – deep dive on the orchestrator and agents.
- `frontend/README.md` – UI-specific commands and structure.
