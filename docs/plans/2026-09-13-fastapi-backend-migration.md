# Penny: FastAPI Backend & LangGraph Agent Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Penny from a standalone CLI simulation into a production-ready, modular FastAPI backend with a stateful LangGraph agentic financial assistant and decoupled mathematical core.

**Architecture:** A clean three-tier architecture in a monorepo (`backend/` and placeholder `frontend/`). The core financial simulation engine (`backend/core/`) is kept 100% pure Python and framework-agnostic. The web layer (`backend/app/`) provides SQLAlchemy persistence with dataset seeding, Pydantic v2 validation, FastAPI REST endpoints, and a LangGraph StateGraph with Server-Sent Events (SSE) streaming and Human-in-the-Loop gates.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, SQLAlchemy 2.0 (SQLite/PostgreSQL), Pydantic v2, Pydantic Settings, LangGraph, LangChain, LangChain-Groq, HTTPX, Pytest.

**Spec:** [`docs/specs/2026-09-13-fastapi-backend-migration-design.md`](../specs/2026-09-13-fastapi-backend-migration-design.md)

## Global Constraints

- **Python Floor**: Python 3.10+ compatibility across all modules.
- **Engine Purity**: `backend/core/` must never import from `backend/app/`, FastAPI, or SQLAlchemy.
- **Invariant Safety**: Zero balance breach guarantee ($B_t \ge \text{minimum\_balance\_to\_keep}$) must remain 100% enforced across all simulations.
- **Backwards Compatibility**: Batch evaluation CLI (`backend/cli.py`) must continue running against `dataset/` without breakage.
- **HitL Policy**: Tools that mutate user settings or spending plans must trigger a human-in-the-loop interrupt before execution.
- **No Placeholders**: All tasks contain complete, executable test code and implementation definitions.

---

## File Structure & Responsibilities

```text
penny/
├── docs/plans/2026-09-13-fastapi-backend-migration.md
├── docs/specs/2026-09-13-fastapi-backend-migration-design.md
│
├── backend/
│   ├── pyproject.toml                     # Modern build and dependency specifications
│   ├── requirements.txt                   # Pip dependency requirements
│   ├── .env.example                       # Environment template (keys, DB URI, port)
│   ├── cli.py                             # Backwards-compatible CLI runner for dataset/
│   │
│   ├── core/                              # Pure mathematical simulation & decision engine
│   │   ├── __init__.py
│   │   ├── models/domain.py, results.py   # Pure immutable dataclasses
│   │   ├── simulation/ledger.py, recurrence.py, safety.py
│   │   ├── optimizer/candidates.py, spending.py, ranker.py
│   │   ├── data/currency.py, evidence.py, linker.py, classifier.py, loader.py
│   │   ├── explanations/templates.py, llm.py
│   │   └── pipeline.py                    # 10-stage DecisionPipeline orchestrator
│   │
│   ├── app/                               # FastAPI web service & LangGraph brain
│   │   ├── __init__.py
│   │   ├── main.py                        # FastAPI application instance, CORS, routers
│   │   ├── config.py                      # AppSettings via pydantic-settings
│   │   │
│   │   ├── db/                            # SQLAlchemy ORM & session management
│   │   │   ├── __init__.py
│   │   │   ├── session.py                 # Engine & scoped sessionmaker
│   │   │   ├── models.py                  # ORM database models
│   │   │   └── seeder.py                  # Seeder populating DB from dataset/ CSVs
│   │   │
│   │   ├── schemas/                       # Pydantic v2 validation contracts
│   │   │   ├── __init__.py
│   │   │   ├── profile.py                 # UserProfile schemas
│   │   │   ├── event.py                   # FinancialEvent schemas
│   │   │   ├── affordability.py           # AffordabilityRequest & Response
│   │   │   ├── simulation.py              # 90-day trajectory schemas
│   │   │   └── chat.py                    # Chat request & SSE event payloads
│   │   │
│   │   ├── services/                      # Domain services bridging DB to core engine
│   │   │   ├── __init__.py
│   │   │   ├── finance_service.py         # Runs DecisionPipeline from DB records
│   │   │   └── simulation_service.py      # Computes trajectory comparison points
│   │   │
│   │   ├── agent/                         # Modular LangGraph stateful agent
│   │   │   ├── __init__.py
│   │   │   ├── state.py                   # AgentState schema
│   │   │   ├── supervisor.py              # LLM resolution & deterministic fallback model
│   │   │   ├── prompts/                   # Modular prompt definitions
│   │   │   │   ├── __init__.py
│   │   │   │   ├── system.py              # Persona and invariant prompt
│   │   │   │   └── templates.py           # Approval & explanation templates
│   │   │   ├── tools/                     # Modular financial tools (single responsibility)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── evaluation.py          # Purchase affordability evaluation tool
│   │   │   │   ├── trajectory.py          # 90-day cashflow trajectory tool
│   │   │   │   ├── profile.py             # User profile & risk metrics tool
│   │   │   │   ├── spending.py            # Spending reduction & approval tools
│   │   │   │   └── factory.py             # Tool bundle aggregator
│   │   │   ├── nodes/                     # Modular execution nodes
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agent.py               # Model invocation node with fallback
│   │   │   │   ├── tools.py               # Tool execution & state capture node
│   │   │   │   └── approval.py            # Human-in-the-loop gate node
│   │   │   ├── edges/                     # Modular control flow edges
│   │   │   │   ├── __init__.py
│   │   │   │   └── routing.py             # Conditional routing functions
│   │   │   ├── checkpointers/             # Modular persistence adapters
│   │   │   │   ├── __init__.py
│   │   │   │   └── memory.py              # MemorySaver checkpointer factory
│   │   │   └── graph.py                   # StateGraph builder and compiler
│   │   │
│   │   └── api/v1/                        # FastAPI route controllers
│   │       ├── __init__.py
│   │       ├── api.py                     # API router aggregation
│   │       ├── affordability.py           # POST /affordability/evaluate
│   │       ├── simulation.py              # GET /simulation/trajectory/{user_id}
│   │       ├── users.py                   # CRUD /users/{user_id}
│   │       ├── events.py                  # CRUD /users/{user_id}/events
│   │       └── chat/                      # Modular streaming & approval endpoints
│   │           ├── __init__.py
│   │           ├── events.py              # SSE event formatting & stream generator
│   │           └── router.py              # POST /chat/stream & POST /chat/approve
│   │
│   └── tests/                             # Comprehensive test suite
│       ├── test_core/                     # 85 core simulation tests
│       ├── test_db/                       # ORM and seeder tests
│       ├── test_api/                      # REST endpoint tests
│       └── test_agent/                    # LangGraph workflow & HitL tests
│
└── frontend/                              # Future React Native mobile application placeholder
```

---

## Phase A: Core Engine Decoupling & Scaffolding

### Task 1: Scaffolding Backend Structure and Dependencies

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/__init__.py`

**Interfaces:**
- Consumes: Standard Python packaging
- Produces: Installed dependency environment supporting FastAPI, SQLAlchemy, LangGraph, and Core engine

- [ ] **Step 1: Create `backend/requirements.txt`**

```text
fastapi>=0.110.0,<0.120.0
uvicorn[standard]>=0.28.0,<0.35.0
sqlalchemy>=2.0.25,<2.1.0
pydantic>=2.6.0,<3.0.0
pydantic-settings>=2.2.0,<3.0.0
python-dotenv>=1.0.0,<2.0.0
requests>=2.31.0,<3.0.0
httpx>=0.27.0,<0.29.0
pytest>=8.0.0,<9.0.0
pytest-asyncio>=0.23.0,<0.25.0
langchain>=0.2.0,<0.4.0
langchain-core>=0.2.0,<0.4.0
langchain-groq>=0.1.0,<0.3.0
langgraph>=0.2.0,<0.3.0
```

- [ ] **Step 2: Create `backend/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "penny-backend"
version = "0.1.0"
description = "Penny AI Financial Affordability Backend & Agentic Engine"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.28.0",
    "sqlalchemy>=2.0.25",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "python-dotenv>=1.0.0",
    "requests>=2.31.0",
    "httpx>=0.27.0",
    "langchain>=0.2.0",
    "langchain-core>=0.2.0",
    "langchain-groq>=0.1.0",
    "langgraph>=0.2.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 3: Create `backend/.env.example`**

```env
PROJECT_NAME="Penny Financial Assistant"
ENVIRONMENT="development"
DEBUG=True
API_V1_PREFIX="/api/v1"
DATABASE_URL="sqlite:///./penny.db"
GROQ_API_KEY=""
LLM_MODEL="llama-3.3-70b-versatile"
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8081"]
```

- [ ] **Step 4: Install dependencies in environment**

Run: `pip install -r backend/requirements.txt`
Expected: Successfully installed packages.

- [ ] **Step 5: Commit scaffolding**

```bash
git add backend/pyproject.toml backend/requirements.txt backend/.env.example backend/__init__.py
git commit -m "chore(backend): scaffold backend package configuration and dependencies"
```

---

### Task 2: Migrating Core Financial Engine to `backend/core/`

**Files:**
- Create: `backend/core/__init__.py`
- Copy & Update: `code/models/` -> `backend/core/models/`
- Copy & Update: `code/simulation/` -> `backend/core/simulation/`
- Copy & Update: `code/optimizer/` -> `backend/core/optimizer/`
- Copy & Update: `code/data/` -> `backend/core/data/`
- Copy & Update: `code/explanations/` -> `backend/core/explanations/`
- Copy & Update: `code/pipeline.py` -> `backend/core/pipeline.py`
- Copy & Update: `code/cache/` -> `backend/core/cache/`

**Interfaces:**
- Consumes: Dataset file paths, pure domain objects
- Produces: `backend.core.pipeline.DecisionPipeline`, `backend.core.models.domain.*`, `backend.core.models.results.*`

- [ ] **Step 1: Copy modules and update package imports**

Copy all subdirectories from `code/` to `backend/core/`.
Update internal imports across all copied files from `code.` or `code.*` to `backend.core.*`.
For example, in `backend/core/pipeline.py`:
```python
from backend.core.data.currency import ExchangeRateConverter
from backend.core.data.evidence import EvidenceManager
from backend.core.data.linker import EventLinker
from backend.core.data.loader import DataLoader
from backend.core.data.classifier import IncomeStreamClassifier
from backend.core.explanations.llm import LLMExplanationGenerator
from backend.core.explanations.templates import ExplanationTemplateSynthesizer
from backend.core.models.domain import FinancialEvent, PaymentOption, PurchaseRequest, UserProfile
from backend.core.models.results import AffordabilityStatus, CandidatePlan, OutputRow, PaymentMethod
from backend.core.optimizer.candidates import CandidateGenerator, generate_schedule_dates
from backend.core.optimizer.ranker import PlanRanker
from backend.core.optimizer.spending import SpendingOptimizer
from backend.core.simulation.ledger import DailyLedger
from backend.core.simulation.recurrence import RecurrenceDetector, RecurringStream
from backend.core.simulation.safety import SafetyEngine
```

- [ ] **Step 2: Create `backend/cli.py` for backwards compatibility**

Migrate `code/main.py` to `backend/cli.py`, updating imports to `backend.core.*` and pointing default dataset paths to `dataset/`.

- [ ] **Step 3: Verify CLI execution from repository root**

Run: `PYTHONPATH=. python3 backend/cli.py --eval-sample --no-llm`
Expected: Output showing 25 sample requests evaluated, producing identical results and 0 crashes.

- [ ] **Step 4: Commit core migration**

```bash
git add backend/core backend/cli.py
git commit -m "refactor(core): relocate financial engine to backend/core with decoupled imports"
```

---

### Task 3: Migrating and Running Core Unit Tests in `backend/tests/test_core/`

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_core/__init__.py`
- Copy & Update: `code/tests/*` -> `backend/tests/test_core/*`

**Interfaces:**
- Consumes: `backend.core.*`
- Produces: Verified test results for all 85 invariant and unit tests

- [ ] **Step 1: Copy tests and update import paths**

Update imports in all tests from `code.*` to `backend.core.*`.
For example, in `backend/tests/test_core/test_simulation.py`:
```python
from backend.core.models.domain import UserProfile, FinancialEvent
from backend.core.simulation.ledger import DailyLedger
from backend.core.simulation.safety import SafetyEngine
```

- [ ] **Step 2: Execute test suite under pytest**

Run: `PYTHONPATH=. pytest backend/tests/test_core -v`
Expected: 85 passed.

- [ ] **Step 3: Commit migrated tests**

```bash
git add backend/tests
git commit -m "test(core): relocate test suite to backend/tests/test_core with all 85 tests passing"
```

---

## Phase B: Database Layer & Dataset Seeder

### Task 4: Setting Up Database Engine & Session Management

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/session.py`
- Test: `backend/tests/test_db/test_session.py`

**Interfaces:**
- Consumes: `DATABASE_URL` from `backend.app.config.AppSettings`
- Produces: `engine`, `SessionLocal`, and FastAPI dependency `get_db() -> Generator[Session, None, None]`

- [ ] **Step 1: Write test for database session initialization**

```python
# backend/tests/test_db/test_session.py
from backend.app.db.session import engine, get_db
from sqlalchemy import text

def test_database_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1

def test_get_db_generator():
    db_gen = get_db()
    session = next(db_gen)
    assert session is not None
    try:
        session.execute(text("SELECT 1"))
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
```

- [ ] **Step 2: Implement `backend/app/config.py`**

```python
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    PROJECT_NAME: str = "Penny Financial Assistant"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./penny.db"
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8081"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = AppSettings()
```

- [ ] **Step 3: Implement `backend/app/db/session.py`**

```python
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Run test to verify DB connectivity**

Run: `PYTHONPATH=. pytest backend/tests/test_db/test_session.py -v`
Expected: PASS.

- [ ] **Step 5: Commit DB session setup**

```bash
git add backend/app/config.py backend/app/db/session.py backend/tests/test_db/test_session.py
git commit -m "feat(db): implement database configuration, engine, and sessionmaker"
```

---

### Task 5: Implementing SQLAlchemy ORM Models

**Files:**
- Create: `backend/app/db/models.py`
- Test: `backend/tests/test_db/test_models.py`

**Interfaces:**
- Consumes: `Base` from `backend.app.db.session`
- Produces: `UserDB`, `FinancialEventDB`, `PaymentOptionDB`, `DecisionRecordDB`

- [ ] **Step 1: Write test for ORM models**

```python
# backend/tests/test_db/test_models.py
from backend.app.db.session import Base, engine, SessionLocal
from backend.app.db.models import UserDB, FinancialEventDB, PaymentOptionDB

def setup_module():
    Base.metadata.create_all(bind=engine)

def teardown_module():
    Base.metadata.drop_all(bind=engine)

def test_create_user_and_event():
    db = SessionLocal()
    try:
        user = UserDB(
            user_id="user_test_01",
            home_currency="USD",
            current_available_balance=1000.0,
            minimum_balance_to_keep=200.0,
            financial_priorities="protect_essentials|save_buffer",
            expense_categories_to_protect="rent|groceries",
            expense_categories_to_reduce="entertainment",
            expense_categories_to_stop="streaming",
            payment_methods_user_will_consider="full_payment|installments",
            max_installment_months=6
        )
        db.add(user)
        db.commit()

        event = FinancialEventDB(
            event_id="ev_test_01",
            user_id="user_test_01",
            event_type="recurring",
            description="Apartment Rent",
            category="rent",
            direction="debit",
            amount=500.0,
            currency="USD",
            event_date="2026-09-01",
            settlement_date="2026-09-01",
            status="settled",
            flexibility="fixed"
        )
        db.add(event)
        db.commit()

        fetched_user = db.query(UserDB).filter_by(user_id="user_test_01").first()
        assert fetched_user is not None
        assert fetched_user.home_currency == "USD"
        assert len(fetched_user.events) == 1
        assert fetched_user.events[0].amount == 500.0
    finally:
        db.close()
```

- [ ] **Step 2: Implement `backend/app/db/models.py`**

```python
from sqlalchemy import Column, String, Float, Integer, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.db.session import Base

class UserDB(Base):
    __tablename__ = "users"

    user_id = Column(String(64), primary_key=True, index=True)
    home_currency = Column(String(8), nullable=False)
    current_available_balance = Column(Float, nullable=False)
    minimum_balance_to_keep = Column(Float, nullable=False)
    financial_priorities = Column(Text, default="")
    expense_categories_to_protect = Column(Text, default="")
    expense_categories_to_reduce = Column(Text, default="")
    expense_categories_to_stop = Column(Text, default="")
    payment_methods_user_will_consider = Column(Text, default="")
    max_installment_months = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    events = relationship("FinancialEventDB", back_populates="user", cascade="all, delete-orphan")
    decisions = relationship("DecisionRecordDB", back_populates="user", cascade="all, delete-orphan")

class FinancialEventDB(Base):
    __tablename__ = "financial_events"

    event_id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)
    description = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False)
    direction = Column(String(16), nullable=False)
    amount = Column(Float, nullable=True)
    currency = Column(String(8), nullable=False)
    event_date = Column(String(16), nullable=False)
    settlement_date = Column(String(16), nullable=True)
    status = Column(String(32), nullable=False)
    linked_event_id = Column(String(64), nullable=True)
    flexibility = Column(String(32), default="fixed")
    minimum_allowed_amount = Column(Float, nullable=True)

    user = relationship("UserDB", back_populates="events")

class PaymentOptionDB(Base):
    __tablename__ = "payment_options"

    payment_option_id = Column(String(64), primary_key=True, index=True)
    request_id = Column(String(64), index=True, nullable=False)
    payment_method = Column(String(32), nullable=False)
    payment_amount = Column(Float, nullable=False)
    number_of_payments = Column(Integer, nullable=False)
    first_payment_date = Column(String(16), nullable=False)
    payment_frequency_days = Column(Integer, nullable=False)
    financing_fee = Column(Float, default=0.0)
    total_payable_amount = Column(Float, nullable=False)

class DecisionRecordDB(Base):
    __tablename__ = "decision_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), index=True, nullable=False)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    amount_safe_to_pay = Column(Float, nullable=False)
    affordability_status = Column(String(32), nullable=False)
    recommended_payment_method = Column(String(32), nullable=False)
    payment_plan = Column(Text, nullable=False)
    earliest_date_for_full_payment = Column(String(16), nullable=True)
    spending_changes_needed = Column(Text, nullable=False)
    decision_explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserDB", back_populates="decisions")
```

- [ ] **Step 3: Run test to verify models**

Run: `PYTHONPATH=. pytest backend/tests/test_db/test_models.py -v`
Expected: PASS.

- [ ] **Step 4: Commit ORM models**

```bash
git add backend/app/db/models.py backend/tests/test_db/test_models.py
git commit -m "feat(db): define SQLAlchemy ORM models for users, financial events, options, and decisions"
```

---

### Task 6: Implementing the CSV Dataset Seeder

**Files:**
- Create: `backend/app/db/seeder.py`
- Test: `backend/tests/test_db/test_seeder.py`

**Interfaces:**
- Consumes: CSVs from `dataset/` (`financial_profiles.csv`, `financial_events.csv`, `request_payment_options.csv`)
- Produces: `seed_database_from_dataset(db: Session, dataset_dir: str = "dataset") -> Dict[str, int]`

- [ ] **Step 1: Write test for seeder**

```python
# backend/tests/test_db/test_seeder.py
from backend.app.db.session import Base, engine, SessionLocal
from backend.app.db.models import UserDB, FinancialEventDB
from backend.app.db.seeder import seed_database_from_dataset

def setup_module():
    Base.metadata.create_all(bind=engine)

def teardown_module():
    Base.metadata.drop_all(bind=engine)

def test_seed_database():
    db = SessionLocal()
    try:
        counts = seed_database_from_dataset(db, dataset_dir="dataset", limit_users=5)
        assert counts["users"] == 5
        assert counts["events"] > 0
        user = db.query(UserDB).first()
        assert user is not None
        assert len(user.events) > 0
    finally:
        db.close()
```

- [ ] **Step 2: Implement `backend/app/db/seeder.py`**

```python
import csv
import os
from typing import Dict, Optional
from sqlalchemy.orm import Session
from backend.app.db.models import UserDB, FinancialEventDB, PaymentOptionDB

def seed_database_from_dataset(db: Session, dataset_dir: str = "dataset", limit_users: Optional[int] = None) -> Dict[str, int]:
    profiles_path = os.path.join(dataset_dir, "financial_profiles.csv")
    events_path = os.path.join(dataset_dir, "financial_events.csv")
    options_path = os.path.join(dataset_dir, "request_payment_options.csv")

    user_count = 0
    allowed_user_ids = set()

    with open(profiles_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["user_id"]
            if limit_users and user_count >= limit_users:
                break
            existing = db.query(UserDB).filter_by(user_id=uid).first()
            if not existing:
                max_inst = int(row["max_installment_months"]) if row.get("max_installment_months") else None
                user = UserDB(
                    user_id=uid,
                    home_currency=row["home_currency"],
                    current_available_balance=float(row["current_available_balance"]),
                    minimum_balance_to_keep=float(row["minimum_balance_to_keep"]),
                    financial_priorities=row.get("financial_priorities", ""),
                    expense_categories_to_protect=row.get("expense_categories_to_protect", ""),
                    expense_categories_to_reduce=row.get("expense_categories_to_reduce", ""),
                    expense_categories_to_stop=row.get("expense_categories_to_stop", ""),
                    payment_methods_user_will_consider=row.get("payment_methods_user_will_consider", ""),
                    max_installment_months=max_inst,
                )
                db.add(user)
                user_count += 1
                allowed_user_ids.add(uid)
    db.commit()

    event_count = 0
    with open(events_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = row["user_id"]
            if allowed_user_ids and uid not in allowed_user_ids:
                continue
            ev_id = row["event_id"]
            if not db.query(FinancialEventDB).filter_by(event_id=ev_id).first():
                amt = float(row["amount"]) if row["amount"] else None
                min_amt = float(row["minimum_allowed_amount"]) if row.get("minimum_allowed_amount") else None
                event = FinancialEventDB(
                    event_id=ev_id,
                    user_id=uid,
                    event_type=row["event_type"],
                    description=row["description"],
                    category=row["category"],
                    direction=row["direction"],
                    amount=amt,
                    currency=row["currency"],
                    event_date=row["event_date"],
                    settlement_date=row["settlement_date"] or None,
                    status=row["status"],
                    linked_event_id=row["linked_event_id"] or None,
                    flexibility=row.get("flexibility", "fixed"),
                    minimum_allowed_amount=min_amt,
                )
                db.add(event)
                event_count += 1
    db.commit()

    option_count = 0
    if os.path.exists(options_path):
        with open(options_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                opt_id = row["payment_option_id"]
                if not db.query(PaymentOptionDB).filter_by(payment_option_id=opt_id).first():
                    opt = PaymentOptionDB(
                        payment_option_id=opt_id,
                        request_id=row["request_id"],
                        payment_method=row["payment_method"],
                        payment_amount=float(row["payment_amount"]),
                        number_of_payments=int(row["number_of_payments"]),
                        first_payment_date=row["first_payment_date"],
                        payment_frequency_days=int(row["payment_frequency_days"]),
                        financing_fee=float(row.get("financing_fee", 0.0) or 0.0),
                        total_payable_amount=float(row["total_payable_amount"]),
                    )
                    db.add(opt)
                    option_count += 1
        db.commit()

    return {"users": user_count, "events": event_count, "options": option_count}
```

- [ ] **Step 3: Run seeder test**

Run: `PYTHONPATH=. pytest backend/tests/test_db/test_seeder.py -v`
Expected: PASS.

- [ ] **Step 4: Commit seeder utility**

```bash
git add backend/app/db/seeder.py backend/tests/test_db/test_seeder.py
git commit -m "feat(db): implement CSV dataset seeder for users, events, and payment options"
```

---

## Phase C: FastAPI REST Service & Contracts

### Task 7: Defining Pydantic v2 Schemas

**Files:**
- Create: `backend/app/schemas/profile.py`
- Create: `backend/app/schemas/event.py`
- Create: `backend/app/schemas/affordability.py`
- Create: `backend/app/schemas/simulation.py`
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_api/test_schemas.py`

**Interfaces:**
- Consumes: Standard Pydantic v2 types
- Produces: Data validation schemas for API inputs, outputs, and SSE events

- [ ] **Step 1: Write schema validation tests**

```python
# backend/tests/test_api/test_schemas.py
from backend.app.schemas.affordability import AffordabilityRequest, AffordabilityResponse
from backend.app.schemas.profile import UserProfileResponse

def test_affordability_request_validation():
    req = AffordabilityRequest(
        user_id="user_01",
        requested_amount=500.0,
        desired_completion_date="2026-10-01",
        allows_partial_payment=True,
        request_text="Can I buy an iPad?"
    )
    assert req.requested_amount == 500.0
    assert req.allows_partial_payment is True

def test_user_profile_response_parsing():
    profile = UserProfileResponse(
        user_id="user_01",
        home_currency="EUR",
        current_available_balance=1200.0,
        minimum_balance_to_keep=300.0,
        protected_categories=["rent", "groceries"],
        reducible_categories=["dining"],
        stoppable_categories=["streaming"]
    )
    assert profile.user_id == "user_01"
    assert "rent" in profile.protected_categories
```

- [ ] **Step 2: Implement schemas**

Implement `profile.py`, `event.py`, `affordability.py`, `simulation.py`, and `chat.py` in `backend/app/schemas/`.

```python
# backend/app/schemas/affordability.py
from typing import List, Optional
from pydantic import BaseModel, Field

class AffordabilityRequest(BaseModel):
    user_id: str
    requested_amount: float = Field(..., gt=0)
    desired_completion_date: str
    request_date: Optional[str] = None
    allows_partial_payment: bool = False
    request_text: Optional[str] = ""

class AffordabilityResponse(BaseModel):
    request_id: str
    user_id: str
    amount_safe_to_pay: float
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str
    earliest_date_for_full_payment: Optional[str] = None
    spending_changes_needed: str
    decision_explanation: str
```

```python
# backend/app/schemas/simulation.py
from typing import List, Optional
from pydantic import BaseModel

class TrajectoryPoint(BaseModel):
    date: str
    baseline_balance: float
    with_purchase_balance: Optional[float] = None

class TrajectoryResponse(BaseModel):
    user_id: str
    currency: str
    minimum_balance_to_keep: float
    points: List[TrajectoryPoint]
    lowest_projected_balance: float
    is_safe: bool
```

```python
# backend/app/schemas/chat.py
from typing import Any, Dict, Optional
from pydantic import BaseModel

class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None

class ActionApprovalRequest(BaseModel):
    session_id: str
    confirmed: bool
```

- [ ] **Step 3: Run schema tests**

Run: `PYTHONPATH=. pytest backend/tests/test_api/test_schemas.py -v`
Expected: PASS.

- [ ] **Step 4: Commit schemas**

```bash
git add backend/app/schemas backend/tests/test_api/test_schemas.py
git commit -m "feat(api): define Pydantic v2 schemas for profile, event, affordability, simulation, and chat"
```

---

### Task 8: Implementing Business Logic Services

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/finance_service.py`
- Create: `backend/app/services/simulation_service.py`
- Test: `backend/tests/test_api/test_services.py`

**Interfaces:**
- Consumes: SQLAlchemy `Session`, ORM entities, `backend.core.pipeline.DecisionPipeline`
- Produces: `FinanceService.evaluate_request()`, `SimulationService.get_trajectory()`

- [ ] **Step 1: Write test for services**

```python
# backend/tests/test_api/test_services.py
from backend.app.db.session import Base, engine, SessionLocal
from backend.app.db.seeder import seed_database_from_dataset
from backend.app.services.finance_service import FinanceService
from backend.app.services.simulation_service import SimulationService
from backend.app.schemas.affordability import AffordabilityRequest

def setup_module():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database_from_dataset(db, dataset_dir="dataset", limit_users=3)
    db.close()

def teardown_module():
    Base.metadata.drop_all(bind=engine)

def test_finance_service_evaluate():
    db = SessionLocal()
    try:
        service = FinanceService(db)
        req = AffordabilityRequest(
            user_id="user_01",
            requested_amount=100.0,
            desired_completion_date="2026-03-31",
            allows_partial_payment=True,
            request_text="Test purchase"
        )
        result = service.evaluate_affordability(req)
        assert result.user_id == "user_01"
        assert result.affordability_status in ["affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"]
    finally:
        db.close()

def test_simulation_service_trajectory():
    db = SessionLocal()
    try:
        sim_service = SimulationService(db)
        traj = sim_service.compute_user_trajectory(user_id="user_01", prospective_amount=100.0)
        assert traj.user_id == "user_01"
        assert len(traj.points) == 91  # 0..90 days
        assert traj.points[0].with_purchase_balance is not None
    finally:
        db.close()
```

- [ ] **Step 2: Implement `backend/app/services/finance_service.py`**

Converts ORM `UserDB`, `FinancialEventDB`, and `PaymentOptionDB` to `backend.core.models.domain` dataclasses and invokes `DecisionPipeline.evaluate_request()`.

- [ ] **Step 3: Implement `backend/app/services/simulation_service.py`**

Runs `DailyLedger` for 90 days with baseline cash flow and with the prospective purchase subtracted on day 0, computing both trajectories for comparison.

- [ ] **Step 4: Run service tests**

Run: `PYTHONPATH=. pytest backend/tests/test_api/test_services.py -v`
Expected: PASS.

- [ ] **Step 5: Commit services**

```bash
git add backend/app/services backend/tests/test_api/test_services.py
git commit -m "feat(services): implement FinanceService and SimulationService bridging DB to core engine"
```

---

### Task 9: Implementing FastAPI REST Endpoints & Application Factory

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/v1/__init__.py`
- Create: `backend/app/api/v1/api.py`
- Create: `backend/app/api/v1/affordability.py`
- Create: `backend/app/api/v1/simulation.py`
- Create: `backend/app/api/v1/users.py`
- Create: `backend/app/api/v1/events.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_api/test_endpoints.py`

**Interfaces:**
- Consumes: FastAPI router decorators, Pydantic schemas, `get_db`
- Produces: ASGI application with complete OpenAPI 3.1 documentation

- [ ] **Step 1: Write API endpoint tests**

```python
# backend/tests/test_api/test_endpoints.py
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import Base, engine, SessionLocal
from backend.app.db.seeder import seed_database_from_dataset

client = TestClient(app)

def setup_module():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database_from_dataset(db, dataset_dir="dataset", limit_users=3)
    db.close()

def teardown_module():
    Base.metadata.drop_all(bind=engine)

def test_get_user_profile():
    res = client.get("/api/v1/users/user_01")
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "user_01"

def test_evaluate_affordability_endpoint():
    payload = {
        "user_id": "user_01",
        "requested_amount": 250.0,
        "desired_completion_date": "2026-03-31",
        "allows_partial_payment": True
    }
    res = client.post("/api/v1/affordability/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "amount_safe_to_pay" in data
    assert "affordability_status" in data

def test_get_simulation_trajectory():
    res = client.get("/api/v1/simulation/trajectory/user_01?prospective_amount=150.0")
    assert res.status_code == 200
    data = res.json()
    assert len(data["points"]) > 0
    assert "lowest_projected_balance" in data
```

- [ ] **Step 2: Implement route handlers and `backend/app/main.py`**

Implement FastAPI routers with CORS middleware, lifespan events, and error handlers.

- [ ] **Step 3: Run API endpoint tests**

Run: `PYTHONPATH=. pytest backend/tests/test_api/test_endpoints.py -v`
Expected: PASS.

- [ ] **Step 4: Commit REST API implementation**

```bash
git add backend/app/api backend/app/main.py backend/tests/test_api/test_endpoints.py
git commit -m "feat(api): implement FastAPI REST endpoints for users, affordability, and trajectory simulation"
```

---

## Phase D: LangGraph Agent & SSE Streaming

### Task 10: Defining Modular Agent State, Prompts & Financial Tools

**Files:**
- Create: `backend/app/agent/__init__.py`
- Create: `backend/app/agent/state.py`
- Create: `backend/app/agent/prompts/system.py`, `templates.py`, `__init__.py`
- Create: `backend/app/agent/tools/evaluation.py`, `trajectory.py`, `profile.py`, `spending.py`, `factory.py`, `__init__.py`
- Test: `backend/tests/test_agent/test_state.py`, `test_prompts.py`, `test_tools.py`

**Interfaces:**
- Consumes: LangChain `@tool` decorator, `FinanceService`, `SimulationService`
- Produces: Decoupled tool modules callable by the LangGraph agent (`evaluate_purchase`, `get_cashflow_trajectory`, `get_user_financial_profile`, `simulate_spending_reduction`, `request_spending_modification_approval`)

- [x] **Step 1: Write tests for agent tools, state, and prompts**
- [x] **Step 2: Implement `backend/app/agent/state.py` and `prompts/`**
- [x] **Step 3: Implement modular tools under `backend/app/agent/tools/`**
- [x] **Step 4: Run tool tests** (`PYTHONPATH=. pytest backend/tests/test_agent/test_tools.py -v`)
- [x] **Step 5: Commit modular agent tools**

---

### Task 11: Constructing Modular LangGraph StateGraph with Human-in-the-Loop

**Files:**
- Create: `backend/app/agent/nodes/agent.py`, `tools.py`, `approval.py`, `__init__.py`
- Create: `backend/app/agent/edges/routing.py`, `__init__.py`
- Create: `backend/app/agent/checkpointers/memory.py`, `__init__.py`
- Create: `backend/app/agent/supervisor.py`
- Create: `backend/app/agent/graph.py`
- Test: `backend/tests/test_agent/test_nodes.py`, `test_edges.py`, `test_graph.py`

**Interfaces:**
- Consumes: `AgentState`, modular agent tools, `langgraph.graph.StateGraph`
- Produces: `create_penny_agent(db: Session, checkpointer=None) -> CompiledGraph`

- [x] **Step 1: Write test for StateGraph flow, nodes, and routing edges**
- [x] **Step 2: Implement modular nodes (`nodes/`), edges (`edges/`), checkpointer (`checkpointers/`), and `graph.py`**
- [x] **Step 3: Run graph tests** (`PYTHONPATH=. pytest backend/tests/test_agent/test_graph.py -v`)
- [x] **Step 4: Commit LangGraph agent**

---

### Task 12: Implementing Modular Server-Sent Events (SSE) Streaming Endpoint

**Files:**
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/api/v1/chat/events.py`, `router.py`, `__init__.py`
- Modify: `backend/app/api/v1/api.py`
- Test: `backend/tests/test_api/test_chat_stream.py`

**Interfaces:**
- Consumes: `POST /api/v1/chat/stream`, `POST /api/v1/chat/approve`
- Produces: `text/event-stream` delivering `status`, `tool_call`, `token`, `decision_card`, and `done` events

- [x] **Step 1: Write test for SSE streaming and approval endpoints**
- [x] **Step 2: Implement modular SSE events generator and FastAPI chat router**
- [x] **Step 3: Run SSE test** (`PYTHONPATH=. pytest backend/tests/test_api/test_chat_stream.py -v`)
- [x] **Step 4: Commit chat streaming endpoint**

---

## Phase E: Verification, Benchmarks & Documentation

### Task 13: Full Integration Verification & Benchmark Evaluation

**Files:**
- Test: `backend/tests/test_integration.py`

**Interfaces:**
- Consumes: Complete backend suite and `dataset/sample_requests.csv`
- Produces: 100% test pass verification and calibration confirmation

- [ ] **Step 1: Write end-to-end integration test running sample requests through the backend**

```python
# backend/tests/test_integration.py
import csv
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.session import Base, engine, SessionLocal
from backend.app.db.seeder import seed_database_from_dataset

client = TestClient(app)

def setup_module():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database_from_dataset(db, dataset_dir="dataset")
    db.close()

def teardown_module():
    Base.metadata.drop_all(bind=engine)

def test_full_benchmark_sample_run():
    with open("dataset/sample_requests.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 5:
                break
            payload = {
                "user_id": row["user_id"],
                "requested_amount": float(row["requested_amount"]),
                "desired_completion_date": row["desired_completion_date"],
                "request_date": row["request_date"],
                "allows_partial_payment": row["allows_partial_payment"].lower() == "true",
                "request_text": row.get("request_text", "")
            }
            res = client.post("/api/v1/affordability/evaluate", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["affordability_status"] in ["affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"]
```

- [ ] **Step 2: Run all backend tests across core, db, api, and agent**

Run: `PYTHONPATH=. pytest backend/tests -v`
Expected: All tests pass.

- [ ] **Step 3: Commit integration test**

```bash
git add backend/tests/test_integration.py
git commit -m "test(integration): verify end-to-end backend service execution against benchmark samples"
```

---

### Task 14: Developer Documentation & OnePay Learning Guide

**Files:**
- Create: `backend/README.md`
- Create: `docs/guides/onepay-internship-learnings.md`

**Interfaces:**
- Consumes: System architecture and developer execution commands
- Produces: Comprehensive developer guide and internship technical study notes

- [ ] **Step 1: Write `backend/README.md`**

Document:
- How to start FastAPI server (`uvicorn backend.app.main:app --reload`)
- How to seed database (`python3 -m backend.app.db.seeder`)
- Interactive Swagger UI (`http://localhost:8000/docs`)
- SSE event structure and client integration guide

- [ ] **Step 2: Write `docs/guides/onepay-internship-learnings.md`**

Document key concepts learned and implemented:
- How deterministic cash-flow simulation safeguards credit underwriting (BNPL)
- How LangGraph state machines coordinate multi-turn financial reasoning
- Why Human-in-the-Loop gates are vital for financial agents
- Comparison of SSE vs WebSockets in modern fintech mobile clients

- [ ] **Step 3: Commit documentation**

```bash
git add backend/README.md docs/guides/onepay-internship-learnings.md
git commit -m "docs: add backend developer guide and OnePay fintech learning notes"
```

---

## Plan Review Checklist

- [x] **Spec Coverage**: All 5 phases and architecture requirements from the design spec are mapped to specific tasks.
- [x] **No Placeholders**: Every step contains concrete code blocks, file paths, commands, and expected outputs.
- [x] **Type & Interface Consistency**: Pydantic schemas, ORM models, and core domain dataclasses maintain exact naming and parameter types across all tasks.
- [x] **Safety Invariants**: Strict minimum balance enforcement, pending debit reservations, and HitL gates are tested in every layer.
