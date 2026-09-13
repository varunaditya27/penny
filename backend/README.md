<div align="center">

# 🪙 Penny — Backend Service & Financial Engine

**High-Performance FastAPI Service & Deterministic Cash-Flow Simulation Engine**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-e92063.svg)](https://docs.pydantic.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/tests-105%20passed-success.svg)]()

</div>

---

## 📌 Architecture Overview

Penny's backend is engineered around a **strictly decoupled two-tier architecture**:

```text
┌─────────────────────────────────────────────────────────────┐
│                    API & Persistence Layer                  │
│                        (backend/app/)                       │
│  FastAPI Endpoints • SQLAlchemy ORM • Pydantic v2 Validation│
└──────────────────────────────┬──────────────────────────────┘
                               │ maps DB rows to domain models
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Core Financial Domain Engine                │
│                       (backend/core/)                       │
│  90-Day DailyLedger • RecurrenceDetector • CandidateGen     │
│    SpendingOptimizer • 6-Tier Ranker • BFS FX Converter     │
│          (Pure Python — Zero Framework Dependencies)        │
└─────────────────────────────────────────────────────────────┘
```

1. **`backend/app/` (Service Layer)**:
   - FastAPI application routing, dependency injection (`get_db`), CORS, and lifespan management.
   - Pydantic v2 request/response contracts ensuring strict typing, validation, and auto-generated OpenAPI schemas.
   - SQLAlchemy 2.0 ORM models and SQLite / PostgreSQL connection pooling.
   - Domain orchestration services (`FinanceService`, `SimulationService`) bridging persistent storage to the simulation domain.

2. **`backend/core/` (Domain Layer)**:
   - **Zero framework dependencies**: Has zero imports from FastAPI, SQLAlchemy, or Pydantic. Uses standard Python dataclasses and math.
   - **Forward 90-day cash-flow simulation ledger**: Simulates daily balance trajectories $B_t = B_{t-1} + \text{Credits}_t - \text{Debits}_t$ enforcing user minimum balance floors.
   - **Recurrence detection**: Discovers calendar Day-of-Month (DOM) streams and integer day-step cadences.
   - **Multi-currency graph**: BFS triangulation and rate inversion across EUR, USD, INR, IDR, and ZAR.
   - **6-tier lexicographic ranker**: Deterministically resolves ties across candidate plans.

---

## 📂 Directory Layout

```text
backend/
├── README.md                      # You are here: Backend developer guide
├── ARCHITECTURE.md                # Comprehensive architectural and mathematical specification
├── pyproject.toml                 # Packaging metadata, tools config, and dependencies
├── requirements.txt               # Direct pip/uv package dependencies
├── cli.py                         # CLI driver for batch dataset runs and benchmark evaluation
│
├── app/                           # ⚡ FastAPI Service & Persistence Layer
│   ├── main.py                    # App factory, CORS middleware & lifespan DB creation
│   ├── config.py                  # Pydantic BaseSettings loading from .env
│   ├── api/                       # API router definitions
│   │   └── v1/
│   │       ├── api.py             # Top-level API router aggregator
│   │       ├── users.py           # User profile and cash-flow risk metrics endpoints
│   │       ├── events.py          # User financial events endpoints (GET, POST)
│   │       ├── affordability.py   # Affordability evaluation endpoint (/evaluate)
│   │       └── simulation.py      # 90-day trajectory simulation endpoint (/trajectory)
│   ├── db/                        # Persistence
│   │   ├── session.py             # SQLAlchemy engine and scoped session dependency
│   │   ├── models.py              # UserDB, FinancialEventDB, PaymentOptionDB, DecisionRecordDB
│   │   └── seeder.py              # Batch-optimized CSV dataset seeder
│   ├── schemas/                   # Pydantic v2 data contracts
│   │   ├── profile.py             # UserProfileResponse, UserProfileUpdate, CashFlowRiskMetrics
│   │   ├── event.py               # FinancialEventResponse, FinancialEventCreate
│   │   ├── affordability.py       # AffordabilityRequest, AffordabilityResponse, PaymentOptionInput
│   │   └── simulation.py          # TrajectoryResponse, TrajectoryPoint
│   └── services/                  # Domain orchestration services
│       ├── finance_service.py     # FinanceService (CRUD, risk metrics, affordability evaluation)
│       └── simulation_service.py  # SimulationService (multi-horizon forward trajectory modeling)
│
├── core/                          # 🔬 Pure Python Simulation Domain
│   ├── pipeline.py                # DecisionPipeline coordinating 10-stage evaluation
│   ├── models/                    # Dataclasses (UserProfile, FinancialEvent, CandidatePlan, etc.)
│   ├── data/                      # Ingestion, multi-currency BFS, evidence & event linking
│   ├── simulation/                # 90-day DailyLedger, RecurrenceDetector, SafetyEngine
│   ├── optimizer/                 # CandidateGenerator, SpendingOptimizer, PlanRanker
│   ├── explanations/              # Deterministic templates & optional LLM generator
│   ├── evaluation/                # Ground truth accuracy and token accounting
│   └── cache/                     # Verified precomputed OCR and message mutations
│
├── docs/                          # Architectural specifications and exploratory analysis
│
└── tests/                         # 🧪 Comprehensive Test Suite (105 Tests)
    ├── test_core/                 # 85 domain simulation, recurrence, and optimizer tests
    ├── test_db/                   # 5 database session, ORM, and seeder tests
    └── test_api/                  # 15 FastAPI endpoint and service integration tests
```

---

## 🚀 Getting Started

### 1. Environment Setup

Use `uv` (recommended) or standard `venv`:

```bash
# Using uv (fastest)
uv venv
source .venv/bin/activate
uv pip install -e backend/

# Or using standard pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Configure Environment Variables

```bash
cp backend/.env.example backend/.env
```

Available configuration options in `backend/.env`:
| Key | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./penny.db` | SQLAlchemy connection URL (SQLite or PostgreSQL) |
| `ENVIRONMENT` | `development` | Environment name |
| `DEBUG` | `True` | FastAPI debug mode |
| `GROQ_API_KEY` | `""` | Optional Groq API key for LLM explanation generation |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | LLM model name on Groq |

### 3. Seed Database from Dataset

Populate the database from `dataset/*.csv` files:

```bash
python3 -m backend.app.db.seeder dataset
```

---

## ⚡ Running the API Service

Start the FastAPI ASGI server with auto-reload:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Once running:
- **Interactive OpenAPI Documentation (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative API Documentation (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: `curl http://127.0.0.1:8000/health`

---

## 📡 REST API Reference

### 1. User Profile & Risk Underwriting
- **`GET /api/v1/users/{user_id}`**: Retrieves user balance, preferences, protected categories, and underwriting risk metrics (`monthly_fixed_burn_rate`, `monthly_confirmed_income`, `fixed_cost_ratio`, `discretionary_cashflow`).
- **`PATCH /api/v1/users/{user_id}`**: Updates budget floors, protection lists, or payment method permissions.

### 2. Financial Events
- **`GET /api/v1/users/{user_id}/events`**: Lists all settled, pending, and scheduled events for the user.
- **`POST /api/v1/users/{user_id}/events`**: Adds a new financial event (e.g. recurring bill, upcoming invoice).

### 3. Affordability Decision
- **`POST /api/v1/affordability/evaluate`**: Runs the forward 90-day simulation to evaluate purchase affordability.

**Sample Request**:
```json
{
  "user_id": "user_01",
  "requested_amount": 600.0,
  "desired_completion_date": "2026-03-31",
  "request_date": "2026-01-01",
  "allows_partial_payment": true,
  "request_text": "Ergonomic Office Chair",
  "payment_options": [
    {
      "payment_option_id": "opt_split_3",
      "payment_method": "installments",
      "payment_amount": 200.0,
      "number_of_payments": 3,
      "first_payment_date": "2026-01-01",
      "payment_frequency_days": 30,
      "financing_fee": 0.0,
      "total_payable_amount": 600.0
    }
  ]
}
```

**Sample Response**:
```json
{
  "request_id": "req_8f3a1c20",
  "user_id": "user_01",
  "amount_safe_to_pay": 600.0,
  "affordability_status": "affordable_now",
  "recommended_payment_method": "full_payment",
  "payment_plan": "2026-01-01:600.00",
  "payment_schedule": [
    {
      "date": "2026-01-01",
      "amount": 600.0
    }
  ],
  "earliest_date_for_full_payment": "2026-01-01",
  "spending_changes_needed": "none",
  "spending_changes": [],
  "decision_explanation": "You can afford this in full today without putting your minimum balance at risk."
}
```

### 4. Forward Cash-Flow Trajectory
- **`GET /api/v1/simulation/trajectory/{user_id}?prospective_amount=150.0&days=90`**: Returns daily balance projection curves (both baseline and with-purchase comparison points), lowest projected balance date, and safety buffer margin.

---

## 💻 CLI Usage

Penny provides a CLI entry point at `backend/cli.py` for evaluating dataset requests:

### Run Full Production Pipeline (All 250 requests)
```bash
python3 -m backend.cli --no-llm
```

### Run Benchmark Calibration on Sample Dataset (25 requests)
```bash
python3 -m backend.cli --eval-sample --no-llm
```

---

## 🧪 Testing

Run the complete test suite across all 3 layers:

```bash
PYTHONPATH=. pytest backend/tests/ -v
```

```text
===================== 105 passed in 21.16s ======================
```
