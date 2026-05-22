## Project Structure

```
src/
├── orchestrator/
│   ├── __init__.py
│   ├── state_machine.py      # Core state machine engine
│   ├── events.py             # Event type definitions
│   ├── states.py             # State enum and data
│   └── persistence.py        # State persistence layer
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py         # Abstract agent base class
│   ├── ingestion_agent.py    # Data loading agent
│   ├── exploration_agent.py  # Data profiling agent
│   ├── analysis_agent.py     # Statistical analysis agent
│   ├── visualization_agent.py# Chart generation agent
│   └── reporting_agent.py    # Natural language reporting
│
├── shared/
│   ├── __init__.py
│   ├── context.py            # Shared session context
│   ├── message_bus.py        # Inter-agent communication
│   └── tools.py              # Shared utility functions
│
├── config/
│   ├── __init__.py
│   └── settings.py           # Configuration management
│
└── main.py                   # Application entry point
```
---
## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator (State Machine)                 │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ State Registry  │  │  Event Queue    │  │ Transition      │ │
│  │                 │  │  (asyncio)      │  │ Engine          │ │
│  │ - States        │  │                 │  │                 │ │
│  │ - Handlers      │  │ - Incoming      │  │ - Guards        │ │
│  │ - Persistence   │  │   Events        │  │ - Actions       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Agent Registry                            │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Ingestion   │  │  Exploration │  │   Analysis   │          │
│  │    Agent     │  │    Agent     │  │    Agent     │          │
│  │              │  │              │  │              │          │
│  │ - CSV        │  │ - Profiling  │  │ - Statistics │          │
│  │ - SQL        │  │ - Schema     │  │ - Agg        │          │
│  │ - Excel      │  │ - Quality    │  │ - ML         │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │Visualization │  │   Reporting  │                            │
│  │    Agent     │  │    Agent     │                            │
│  │              │  │              │                            │
│  │ - matplotlib │  │ - Summaries  │                            │
│  │ - plotly     │  │ - Findings   │                            │
│  │ - seaborn    │  │ - Export     │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Shared Context Store                       │
│                                                                 │
│  - Session State (loaded data, current schema)                 │
│  - Query History                                               │
│  - Derived Metrics Cache                                       │
│  - Cross-Agent Memory                                          │
└─────────────────────────────────────────────────────────────────┘
```