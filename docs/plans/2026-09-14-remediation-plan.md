# Backend Comprehensive Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve all 40 findings from the multi-reviewer audit across Security, Performance, Architecture, and Testing to establish an enterprise-grade, high-throughput, and clean FastAPI backend.

**Architecture:** Partition the 40 issues into 5 decoupled, non-colliding domains:
1. **Domain 1 (Core Engine & Simulation)**: Ledger builder extraction, suffix-minimum $O(D)$ date search, inner-loop datetime caching, path anchoring, and unit test coverage for `DecisionPipeline`.
2. **Domain 2 (Database Layer & Models)**: Engine pooling, SQLite WAL pragma, rollback safety in session generator, composite indexes, batch seeder commits, and DB constraint unit tests.
3. **Domain 3 (Schemas, Config & Security Scaffolding)**: Strict Pydantic boundary validation, delimiter injection guards, CORS restrictions, security headers middleware, and environment secret sanitization.
4. **Domain 4 (Services & Presentation API)**: Event pagination (`limit`/`offset`), SQL date filtering in services, singleton pipeline injection, ORM decoupling from `CashFlowRiskService`, custom `UserNotFoundError`, and server-side exception logging.
5. **Domain 5 (API Integration & Test Suite Hardening)**: Complete test coverage for 404/422/unaffordable flows, decision audit persistence verification, and isolation/speedup of test fixtures.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0, SQLite (WAL mode), pytest, starlette.

**Spec:** Multi-Reviewer Audit Report (2026-09-14).

## Global Constraints
- Decoupled Core: `backend/core/` must NEVER import FastAPI, Starlette, Pydantic, or SQLAlchemy.
- Zero AI Slop: No synthetic wrapper classes, no arbitrary sleep statements, no empty exception swallows.
- Total Backward Compatibility: All existing endpoints and CLI commands must remain functional.
- Clean Git State: Work must be verified with all tests passing at each task boundary.

---

### Task 1: Core Simulation Engine & Performance Optimizations (Domain 1)
**Issues Addressed**: [CR-003], [CR-005], [HI-002], [HI-005], [MD-002], [MD-007], [MD-011], [LO-001]

**Files:**
- Create: `backend/core/simulation/builder.py`
- Create: `backend/tests/test_core/test_pipeline.py`
- Modify: `backend/core/simulation/safety.py`
- Modify: `backend/core/simulation/ledger.py`
- Modify: `backend/core/pipeline.py`
- Modify: `backend/core/data/currency.py`
- Modify: `backend/core/data/evidence.py`
- Modify: `backend/core/explanations/llm.py`
- Modify: `backend/tests/test_core/test_models.py`

- [ ] **Step 1: Fix no-op dead assertion in test_models.py**
Remove `if False else None` on line 128 of `backend/tests/test_core/test_models.py` and verify `row.to_csv_row()` directly.
- [ ] **Step 2: Optimize SafetyEngine date search to $O(D)$ via suffix minimum**
In `backend/core/simulation/safety.py`, replace the nested daily loop in `find_earliest_full_payment_date` with a suffix-minimum scan over baseline ledger balances.
- [ ] **Step 3: Optimize inner-loop datetime parsing in DailyLedger**
In `backend/core/simulation/ledger.py`, precompute parsed stream start datetimes before the daily simulation loop instead of invoking `datetime.strptime` on every simulated day.
- [ ] **Step 4: Extract SimulationLedgerBuilder**
In `backend/core/simulation/builder.py`, extract the common pipeline steps (filtering non-cash events, event linking, currency normalization, recurring debit and salary stream resolution) so both `DecisionPipeline` and `SimulationService` share identical simulation inputs.
- [ ] **Step 5: Anchor paths dynamically & use binary search in currency converter**
In `currency.py` and `evidence.py`, resolve dataset paths relative to the repository root using `pathlib.Path(__file__).resolve()`. Use `bisect.bisect_right` for as-of exchange rate dates in `currency.py`. Remove artificial `time.sleep(1.0)` in `llm.py`.
- [ ] **Step 6: Add isolated unit tests for DecisionPipeline**
Create `backend/tests/test_core/test_pipeline.py` covering salary resolution, `STOP_INCOME` evidence, currency conversions, and candidate ranking.
- [ ] **Step 7: Verify core test suite**
Run: `PYTHONPATH=. uv run pytest backend/tests/test_core/ -v`
Expected: All core tests pass.
- [ ] **Step 8: Commit Domain 1 changes**
Run: `git add backend/core/ backend/tests/test_core/ && git commit -m "perf(core): optimize simulation loops, anchor paths, extract ledger builder, and add pipeline tests"`

---

### Task 2: Database Layer, Models, Session & Seeder (Domain 2)
**Issues Addressed**: [CR-004], [HI-014], [MD-003], [MD-004], [MD-006], [MD-013], [LO-004]

**Files:**
- Modify: `backend/app/db/models.py`
- Modify: `backend/app/db/session.py`
- Modify: `backend/app/db/seeder.py`
- Modify: `backend/tests/test_db/test_session.py`
- Modify: `backend/tests/test_db/test_models.py`

- [ ] **Step 1: Fix test isolation in test_session.py**
In `backend/tests/test_db/test_session.py`, monkeypatch or isolate the engine to `sqlite:///:memory:` so `./penny.db` is never created or locked during test runs.
- [ ] **Step 2: Add composite indexes and remove duplicate primary key indexes**
In `backend/app/db/models.py`, add `Index("ix_financial_events_user_date", "user_id", "event_date")` and `Index("ix_decision_records_user_created", "user_id", "created_at")`. Remove redundant `index=True` on primary key columns.
- [ ] **Step 3: Configure connection pooling, WAL mode, and session rollback**
In `backend/app/db/session.py`, add `pool_pre_ping=True`, set `busy_timeout=30.0` for SQLite, enable WAL journal mode pragma on connection, and add `db.rollback()` inside `get_db()` exception block.
- [ ] **Step 4: Optimize Seeder and sanitize dataset path**
In `backend/app/db/seeder.py`, chunk insertions with periodic commits (e.g. batch size 2,000) and canonicalize dataset directory path with `os.path.abspath`.
- [ ] **Step 5: Add tests for PaymentOptionDB and DB constraints**
In `backend/tests/test_db/test_models.py`, add tests for `PaymentOptionDB` persistence, foreign key relationships, and cascade delete behavior.
- [ ] **Step 6: Verify DB test suite**
Run: `PYTHONPATH=. uv run pytest backend/tests/test_db/ -v`
Expected: All database tests pass without generating a local `./penny.db`.
- [ ] **Step 7: Commit Domain 2 changes**
Run: `git add backend/app/db/ backend/tests/test_db/ && git commit -m "feat(db): configure pooling, WAL mode, composite indexes, batch seeder, and constraint tests"`

---

### Task 3: API Schemas, Config, Security Scaffolding & Middleware (Domain 3)
**Issues Addressed**: [CR-001], [CR-002], [HI-009], [HI-010], [HI-011], [MD-010], [MD-012], [MD-014], [LO-002]

**Files:**
- Create: `backend/app/api/deps.py`
- Modify: `.gitignore`
- Modify: `backend/.env`
- Modify: `backend/.env.example`
- Modify: `backend/app/config.py`
- Modify: `backend/app/schemas/event.py`
- Modify: `backend/app/schemas/affordability.py`
- Modify: `backend/app/schemas/profile.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Sanitize .env and ensure global gitignore**
Ensure `**/.env` is ignored. Wipe the plaintext Groq key from `backend/.env` (replace with empty string) and update `backend/.env.example`.
- [ ] **Step 2: Add strict boundary validation and delimiter guards in schemas**
In `schemas/event.py`, `schemas/affordability.py`, and `schemas/profile.py`, enforce `gt=0` on amounts, ISO regex patterns on dates (`^\d{4}-\d{2}-\d{2}$`), ISO currency literals, and validate that list inputs do not contain delimiter characters (`|`, `:`).
- [ ] **Step 3: Clean up public response schemas**
In `schemas/affordability.py`, ensure structured lists (`payment_schedule`, `spending_changes`) are primary and mark raw string serializations as internal/deprecated.
- [ ] **Step 4: Add Auth scaffolding & object-level authorization dependency**
In `backend/app/api/deps.py`, implement an authentication dependency (`get_current_user`) with mock/bypass support for testing and object-level authorization verification (`verify_user_access`).
- [ ] **Step 5: Configure security headers middleware, strict CORS, and conditional docs**
In `backend/app/main.py`, restrict CORS allowed methods and headers, add `SecurityHeadersMiddleware`, and disable `/docs` when `ENVIRONMENT=production`.
- [ ] **Step 6: Verify app startup & schema validation**
Run: `PYTHONPATH=. uv run pytest backend/tests/test_api/test_endpoints.py -v`
- [ ] **Step 7: Commit Domain 3 changes**
Run: `git add .gitignore backend/.env* backend/app/config.py backend/app/schemas/ backend/app/main.py backend/app/api/deps.py && git commit -m "sec(api): add boundary validations, delimiter guards, auth dependency, security headers, and secret sanitization"`

---

### Task 4: Services Layer & API Route Handlers (Domain 4)
**Issues Addressed**: [HI-001], [HI-003], [HI-004], [HI-006], [HI-007], [HI-008], [MD-001], [MD-005], [MD-008], [MD-009], [LO-003]

**Files:**
- Create: `backend/app/services/event_service.py`
- Create: `backend/app/core_exceptions.py` (or `backend/app/exceptions.py`)
- Modify: `backend/app/services/finance_service.py`
- Modify: `backend/app/services/simulation_service.py`
- Modify: `backend/app/services/risk_service.py`
- Modify: `backend/app/services/mappers.py`
- Modify: `backend/app/services/__init__.py`
- Modify: `backend/app/api/v1/users.py`
- Modify: `backend/app/api/v1/events.py`
- Modify: `backend/app/api/v1/affordability.py`
- Modify: `backend/app/api/v1/simulation.py`

- [ ] **Step 1: Define domain exceptions and server logging**
Create `backend/app/exceptions.py` with `UserNotFoundError`. In all route handlers, catch `UserNotFoundError` -> 404, catch generic errors -> log with `logger.exception` and return sanitized 500.
- [ ] **Step 2: Add pagination and service layer for events**
Create `backend/app/services/event_service.py`. Update `GET /api/v1/users/{user_id}/events` to accept `limit: int = 50`, `offset: int = 0` and route database calls through `EventService`. Handle `IntegrityError` in event creation returning 409.
- [ ] **Step 3: Singleton DecisionPipeline and dependency injection**
In `backend/app/api/deps.py`, provide `get_finance_service` and `get_simulation_service` with a shared singleton `DecisionPipeline`. Inject services into route handlers via `Depends()`.
- [ ] **Step 4: SQL-level date filtering in services**
In `finance_service.py` and `simulation_service.py`, filter events by date range directly in SQL rather than loading all user events into memory.
- [ ] **Step 5: Decouple CashFlowRiskService and fix mapper contracts**
Update `CashFlowRiskService.compute_risk_metrics` to accept pure domain entities and normalize foreign currencies. Fix mapper `set` type contracts in `mappers.py` and clean up dead static aliases in `finance_service.py`. Make risk calculation optional on profile read via `include_risk_metrics: bool = False`.
- [ ] **Step 6: Wire SimulationService to shared SimulationLedgerBuilder**
In `simulation_service.py`, replace raw event partitioning with `SimulationLedgerBuilder.build_ledger`.
- [ ] **Step 7: Verify services and endpoints**
Run: `PYTHONPATH=. uv run pytest backend/tests/test_api/ -v`
- [ ] **Step 8: Commit Domain 4 changes**
Run: `git add backend/app/services/ backend/app/api/ backend/app/exceptions.py && git commit -m "refactor(services): introduce event service, pagination, singleton pipeline DI, and unified simulation builder"`

---

### Task 5: Comprehensive API Integration & Test Suite Hardening (Domain 5)
**Issues Addressed**: [HI-012], [HI-013], [MD-015], [MD-016], [LO-005]

**Files:**
- Modify: `backend/tests/test_api/conftest.py`
- Modify: `backend/tests/test_api/test_endpoints.py`
- Modify: `backend/tests/test_api/test_services.py`

- [ ] **Step 1: Optimize test fixtures with session-scoped setup or transactional rollback**
In `conftest.py`, optimize database seeding and engine provisioning so tests do not redundantly re-parse multi-megabyte CSV files on every single test function.
- [ ] **Step 2: Add comprehensive 404, 422, and unaffordable scenario tests**
In `test_endpoints.py`, add tests for nonexistent users (404), invalid schemas / negative amounts (422), out-of-range pagination parameters, and unaffordable purchase evaluations.
- [ ] **Step 3: Tighten response assertions**
Replace weak key-presence assertions (`assert "payment_plan" in data`) with rigorous checks on status enums, non-negative amounts, and structured schedule items.
- [ ] **Step 4: Add tests for DecisionRecordDB persistence and service edge cases**
In `test_services.py`, assert that `DecisionRecordDB` is actually inserted when `save_decision=True`, verify `save_decision=False`, and test missing user exceptions.
- [ ] **Step 5: Run full backend test suite**
Run: `PYTHONPATH=. uv run pytest backend/tests/ -v`
Expected: 100% tests passing with comprehensive coverage across all 40 remediated areas.
- [ ] **Step 6: Commit Domain 5 changes**
Run: `git add backend/tests/ && git commit -m "test(api): add boundary tests, 404/422 cases, persistence assertions, and optimize test fixtures"`
