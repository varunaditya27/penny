# Buy or Wait? Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and package "Buy or Wait?", an evaluable, deterministic AI-powered financial decision agent that evaluates purchase requests against a 90-day cash flow simulation, produces `output.csv`, and generates the required hackathon deliverables (`code.zip`, `evaluation/usage_report.md`).

**Architecture:** A layered architecture with a 100% deterministic Python core for daily balance simulation, currency conversion, recurrence detection, and 6-tier tie-breaking; complemented by versioned JSON caches and targeted Groq API calls (Qwen 3.6 27B for 16 vision receipts, LLaMA 3.3 70B for 215 multilingual messages, and GPT-OSS 20B for hybrid explanation synthesis).

**Tech Stack:** Python 3.10+, Groq Python SDK / HTTP requests, standard library (`csv`, `json`, `dataclasses`, `datetime`, `collections`, `itertools`, `pathlib`, `typing`).

**Spec:** [`code/docs/specs/2026-09-13-buy-or-wait-design.md`](file:///home/varun/Projects/penny/code/docs/specs/2026-09-13-buy-or-wait-design.md)

## Global Constraints

- Must run from the terminal via `python code/main.py`.
- Must generate `output.csv` with exact columns: `request_id,amount_safe_to_pay,affordability_status,recommended_payment_method,payment_plan,earliest_date_for_full_payment,spending_changes_needed,decision_explanation`.
- Must satisfy all invariant rules: $0 \le \text{amount\_safe\_to\_pay} \le \text{requested\_amount}$; balance $\ge \text{minimum\_balance\_to\_keep}$ for all 90 days.
- Must operate gracefully if `GROQ_API_KEY` is not provided (offline autograder fallback).
- Must append per-turn entries to `log.txt` with exact tool name `tool=Antigravity`.
- Must package submission as `code.zip` containing `evaluation/usage_report.md`.

---

## Subsystems & Tasks

### Task 1: Domain & Result Models
**Files:**
- Create: `code/models/__init__.py`
- Create: `code/models/domain.py`
- Create: `code/models/results.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `UserProfile`, `PurchaseRequest`, `FinancialEvent`, `PaymentOption`, `CandidatePlan`, `OutputRow`.

- [ ] **Step 1: Write tests for domain data models**
  - Verify dataclass fields, type coercion, and immutability.
- [ ] **Step 2: Implement domain and result dataclasses**
  - `UserProfile`: `user_id`, `home_currency`, `current_available_balance`, `minimum_balance_to_keep`, sets of protected/reducible/stoppable categories, considered methods, `max_installment_months`.
  - `PurchaseRequest`: `request_id`, `user_id`, `request_date`, `request_type`, `requested_amount`, `desired_completion_date`, `allows_partial_payment`, `request_text`.
  - `FinancialEvent`: `event_id`, `user_id`, `event_type`, `description`, `category`, `direction`, `amount`, `currency`, `event_date`, `settlement_date`, `status`, `linked_event_id`, `flexibility`, `minimum_allowed_amount`.
  - `PaymentOption`: `payment_option_id`, `request_id`, `payment_method`, `payment_amount`, `number_of_payments`, `first_payment_date`, `payment_frequency_days`, `financing_fee`, `total_payable_amount`.
  - `OutputRow`: standard 8 columns matching CSV output specification.
- [ ] **Step 3: Run model tests and verify passing**
- [ ] **Step 4: Commit Task 1**

---

### Task 2: Data Loaders & Currency Conversion
**Files:**
- Create: `code/data/__init__.py`
- Create: `code/data/loader.py`
- Create: `code/data/currency.py`
- Test: `tests/test_data_loader.py`

**Interfaces:**
- Consumes: Models from `code/models/domain.py`.
- Produces: `DataLoader.load_all()`, `ExchangeRateConverter.convert(amount, from_curr, to_curr, date_str)`.

- [ ] **Step 1: Write tests for currency conversion and CSV loading**
  - Test exact dated exchange rate conversions between EUR, INR, IDR, USD, ZAR.
  - Test CSV parser loading requests, profiles, events, and options.
- [ ] **Step 2: Implement `ExchangeRateConverter`**
  - Reads `dataset/exchange_rates.csv` into a composite lookup map `(rate_date, from_currency, to_currency) -> rate`.
  - Converts amounts accurately, returning identity `1.0` if `from_curr == to_curr`.
- [ ] **Step 3: Implement `DataLoader`**
  - Loads and joins datasets cleanly with type casting (floats for amounts, bools for flags).
- [ ] **Step 4: Run loader tests and verify passing**
- [ ] **Step 5: Commit Task 2**

---

### Task 3: Multimodal & Message Evidence Caching
**Files:**
- Create: `code/cache/image_amounts.json`
- Create: `code/cache/message_mutations.json`
- Create: `code/data/evidence.py`
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: Raw images in `dataset/media/images/` and `dataset/messages.csv`.
- Produces: `EvidenceManager.get_image_amount(event_id)`, `EvidenceManager.get_message_mutations(user_id)`.

- [ ] **Step 1: Write verified ground-truth amounts into `code/cache/image_amounts.json`**
  - Populate all 16 extracted values for `event_253`, `event_1442`, `event_1545`, `event_1700`, `event_1786`, `event_3051`, `event_3231`, `event_4535`, `event_5170`, `event_6033`, `event_6859`, `event_7307`, `event_7941`, `event_9421`, `event_9806`, `event_10521`.
- [ ] **Step 2: Pre-extract and verify all 215 message mutations into `code/cache/message_mutations.json`**
  - Parse Indonesian and English salary updates, pending bonus exclusions, and expense increases.
- [ ] **Step 3: Implement `EvidenceManager`**
  - Implements offline cache loading first; falls back to live Groq API (Qwen 3.6 27B / LLaMA 3.3 70B) if `--refresh-cache` flag is passed.
  - Integrates `TokenTracker` to record token counts and costs into `code/evaluation/usage_report.md`.
- [ ] **Step 4: Run evidence tests and verify passing**
- [ ] **Step 5: Commit Task 3**

---

### Task 4: Recurrence Detection Engine
**Files:**
- Create: `code/simulation/__init__.py`
- Create: `code/simulation/recurrence.py`
- Test: `tests/test_recurrence.py`

**Interfaces:**
- Consumes: Historical settled `FinancialEvent` records for a user.
- Produces: `RecurringStream`: detected cadence (DOM vs Day-Step), step size $\Delta d$, baseline amount, latest historical date, and latest historical `event_id`.

- [ ] **Step 1: Write tests for cadence detection**
  - Test weekly (7-day), 10-day, bi-weekly (14-day), 21-day, and 5-day intervals.
  - Test fixed monthly day-of-month recurrence (e.g. rent on 2nd, utility on 6th, salary on 15th).
- [ ] **Step 2: Implement `RecurrenceDetector`**
  - Clusters past settled transactions by `description` and `category`.
  - Validates constant step difference $\Delta d \in \{5, 7, 10, 14, 21\}$ or constant day-of-month ($\ge 2$ occurrences).
  - Tags streams with `latest_event_id` to enable exact `spending_changes_needed` syntax.
- [ ] **Step 3: Run recurrence tests and verify passing**
- [ ] **Step 4: Commit Task 4**

---

### Task 5: 90-Day Balance Ledger & Safety Engine
**Files:**
- Create: `code/simulation/ledger.py`
- Create: `code/simulation/safety.py`
- Test: `tests/test_simulation.py`

**Interfaces:**
- Consumes: `UserProfile`, recurring streams, scheduled events, pending debits, currency converter.
- Produces: `Ledger.simulate(start_date, days=90, payments=None, modifications=None)`, `compute_safe_amount()`, `find_earliest_full_payment_date()`.

- [ ] **Step 1: Write tests for daily ledger simulation**
  - Test that balance never breaches `minimum_balance_to_keep`.
  - Test that pending debits are subtracted on settlement dates and pending credits are ignored.
  - Test that confirmed salary credits on settlement dates replenish balance.
- [ ] **Step 2: Implement `Ledger`**
  - Maintains daily balance array across $[0, 90]$ days from `request_date`.
  - Applies projected recurring events, confirmed future salary credits, and optional candidate payments.
- [ ] **Step 3: Implement `SafetyEngine`**
  - `compute_safe_amount(ledger, requested_amount, min_balance)`: $\min(\text{requested\_amount}, \min_t(\text{balance}_t - \text{min\_balance}))$.
  - `find_earliest_full_payment_date(ledger, requested_amount, min_balance, start_date)`: tests each day $d \in [0, 90]$ for safe full payment without spending modifications.
- [ ] **Step 4: Run simulation tests and verify passing**
- [ ] **Step 5: Commit Task 5**

---

### Task 6: Candidate Generator & 6-Tier Tie-Breaker
**Files:**
- Create: `code/optimizer/__init__.py`
- Create: `code/optimizer/candidates.py`
- Create: `code/optimizer/ranker.py`
- Test: `tests/test_optimizer.py`

**Interfaces:**
- Consumes: `PurchaseRequest`, `UserProfile`, available `PaymentOption` records, `SafetyEngine`.
- Produces: `CandidatePlan` list, `rank_candidate_plans(plans, desired_completion_date)`.

- [ ] **Step 1: Write tests for candidate generation and 6-tier ranking**
  - Test ranking hierarchy: deadline compliance > no changes > min cost > earlier start > fewer payments > lowest option ID.
  - Test payment method filtering based on `payment_methods_user_will_consider` and `max_installment_months`.
- [ ] **Step 2: Implement `CandidateGenerator`**
  - Generates full payment option (if allowed and considered).
  - Generates installment options from `request_payment_options.csv` (filtering by user duration cap and method preference).
  - Generates partial payment option (exactly 2 payments: safe amount today, remainder on earliest date) if conditions met.
  - Generates wait option (full payment on earliest safe date).
- [ ] **Step 3: Implement `PlanRanker`**
  - Encodes 6-tier sorting key into Python tuple.
- [ ] **Step 4: Run optimizer tests and verify passing**
- [ ] **Step 5: Commit Task 6**

---

### Task 7: Spending Adjustment Optimizer
**Files:**
- Create: `code/optimizer/spending.py`
- Test: `tests/test_spending.py`

**Interfaces:**
- Consumes: User eligible recurring streams, profile permissions (`protected`, `reduce`, `stop`).
- Produces: Evaluates subsets of up to 3 non-protected modifications (`stop:<event_id>`, `reduce_to:<event_id>:<min_amount>`).

- [ ] **Step 1: Write tests for spending modification candidate generation**
  - Ensure protected categories are never modified.
  - Ensure reductions set amount to `minimum_allowed_amount`.
  - Ensure max 3 modifications and no double-action on same event.
- [ ] **Step 2: Implement `SpendingAdjuster`**
  - Combinatorially evaluates subsets of size $k \in \{1, 2, 3\}$.
  - Simulates candidate plans under adjusted ledger until a valid plan meeting `desired_completion_date` is found.
- [ ] **Step 3: Run spending tests and verify passing**
- [ ] **Step 4: Commit Task 7**

---

### Task 8: Decision Explanation Synthesizer
**Files:**
- Create: `code/explanations/__init__.py`
- Create: `code/explanations/templates.py`
- Create: `code/explanations/llm.py`
- Test: `tests/test_explanations.py`

**Interfaces:**
- Consumes: Chosen `CandidatePlan`, `UserProfile`, `PurchaseRequest`.
- Produces: Grounded, formatted `decision_explanation` string.

- [ ] **Step 1: Write tests for explanation formatting**
  - Test against sample explanations from `dataset/sample_requests.csv`.
- [ ] **Step 2: Implement deterministic template synthesizer in `templates.py`**
  - Covers `affordable_now`, `wait`, `installments`, and simple `not_recommended` with exact currency formatting and date representations.
- [ ] **Step 3: Implement hybrid LLM generator in `llm.py`**
  - Calls Groq GPT-OSS 20B with few-shot calibration for multi-change spending scenarios.
- [ ] **Step 4: Run explanation tests and verify passing**
- [ ] **Step 5: Commit Task 8**

---

### Task 9: Evaluation Suite & Benchmark Runner
**Files:**
- Create: `code/evaluation/evaluator.py`
- Create: `code/evaluation/main.py`
- Test: `tests/test_evaluator.py`

**Interfaces:**
- Consumes: Predictions and `dataset/sample_requests.csv`.
- Produces: Detailed accuracy report across all 8 output columns.

- [ ] **Step 1: Implement `Evaluator`**
  - Measures exact matches on `affordability_status`, `recommended_payment_method`, `payment_plan`, `earliest_date_for_full_payment`, `spending_changes_needed`, and numerical tolerance on `amount_safe_to_pay`.
- [ ] **Step 2: Connect evaluator CLI in `code/evaluation/main.py`**
- [ ] **Step 3: Commit Task 9**

---

### Task 10: Main CLI Entrypoint & Dual-Mode Pipeline
**Files:**
- Modify: `code/main.py`
- Test: `tests/test_main_cli.py`

**Interfaces:**
- Produces: CLI executing `--eval-sample`, `--refresh-cache`, or default full prediction.

- [ ] **Step 1: Implement CLI argument parsing in `code/main.py`**
  - Handles `--eval-sample`, `--refresh-cache`, and default execution.
- [ ] **Step 2: Implement end-to-end processing pipeline**
  - Orchestrates Data Loading -> Evidence Enhancement -> Ledger Simulation -> Candidate Search -> Tie-Breaking -> Explanation Synthesis -> Output Writing.
  - Writes to both `output.csv` (repo root) and `dataset/output.csv`.
- [ ] **Step 3: Test CLI invocation with terminal run**
- [ ] **Step 4: Commit Task 10**

---

### Task 11: Calibration & Ground Truth Verification
**Files:**
- Validate on `dataset/sample_requests.csv` (25 cases).
- Generate predictions for `dataset/requests.csv` (250 cases).

- [ ] **Step 1: Execute `python code/main.py --eval-sample`**
  - Run full benchmark against all 25 public samples.
  - Diagnose and resolve any discrepancies to reach 100% agreement.
- [ ] **Step 2: Execute `python code/main.py`**
  - Run full prediction across all 250 evaluation requests.
  - Validate output schema (250 rows, 8 columns, no NaNs, valid values).
- [ ] **Step 3: Commit calibrated codebase and generated `output.csv`**

---

### Task 12: Packaging & Deliverable Generation
**Files:**
- Create/Update: `code/evaluation/usage_report.md`
- Create: `code.zip`
- Update: `README.md` with clear setup and execution instructions.

- [ ] **Step 1: Generate `code/evaluation/usage_report.md`**
  - Summarize model providers, names, calls, input/output tokens, and costs across Qwen 3.6 27B, LLaMA 3.3 70B, and GPT-OSS 20B.
- [ ] **Step 2: Update `README.md` with setup, dependencies, and execution instructions**
- [ ] **Step 3: Create clean submission package `code.zip`**
  - Verify that `code.zip` contains runnable code, README, prompts, and `evaluation/usage_report.md` without secrets or `log.txt`.
- [ ] **Step 4: Commit Task 12 and perform final verification check**
