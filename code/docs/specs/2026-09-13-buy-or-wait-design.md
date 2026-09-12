# Design Specification: Buy or Wait? Financial Decision Agent

**Challenge**: HackerRank Orchestrate (September 2026) — *Buy or Wait?*  
**Date**: September 13, 2026  
**Status**: Approved Specification (Enhanced with Empirical Dataset Ground Truth)  
**Authors**: Antigravity & Engineering Team

---

## 1. Executive Summary & Architectural Vision

The **Buy or Wait?** system is an AI-powered financial decision agent designed to evaluate purchase and expense requests (`dataset/requests.csv`). It recommends whether a user should pay in full today, pay partially, take an installment option, wait for a future safe date, or not proceed.

### Core Architectural Demarcation
To prioritize **simplicity, reliability, and determinism**, the system divides responsibilities strictly:
1. **Deterministic Core (100% Python)**:
   - Reconstructs financial profiles, parses dated currency conversions with graph triangulation, detects recurring cash flows (fixed calendar and integer day-step cadences), executes 5-way type dispatch on `linked_event_id`, filters out invalid installment options, simulates daily balance trajectories over 90 days, computes `amount_safe_to_pay` and `earliest_date_for_full_payment`, evaluates candidate plans, and ranks options using a strict 6-tier tie-breaker.
2. **Targeted Groq LLM Integration (Multimodal & Semantic)**:
   - **Qwen 3.6 27B Vision**: Extracts missing numerical amounts from receipts/payslips (`dataset/media/images/*.png`), cached in `code/cache/image_amounts.json`.
   - **Meta LLaMA 3.3 70B**: Extracts structured mutations (`CONFIRM_SALARY`, `NEW_JOB_SALARY`, `CANCEL_EVENT`, `ADJUST_RECURRING_AMOUNT`, `EXCLUDE_PENDING`) from 215 multilingual messages (`dataset/messages.csv`), cached in `code/cache/message_mutations.json`.
   - **OpenAI GPT-OSS 20B**: Enhances explanations for complex multi-spending-change cases, backed by deterministic template synthesis for standard cases.
   - **Token & Cost Tracker**: Logs input/output tokens, model names, and estimated costs into `code/evaluation/usage_report.md`.

---

## 2. Subsystems & Module Structure

```text
code/
├── cache/
│   ├── image_amounts.json           # Ground-truth amounts for 16 missing image events
│   └── message_mutations.json       # Pre-extracted mutation schemas for 215 messages
├── docs/
│   ├── eda_and_problem_statement_correlation.md
│   ├── plans/
│   │   └── 2026-09-13-buy-or-wait-implementation.md
│   └── specs/
│       └── 2026-09-13-buy-or-wait-design.md
├── evaluation/
│   ├── evaluator.py                 # Ground-truth accuracy and calibration test suite
│   ├── main.py                      # Evaluator CLI entrypoint
│   └── usage_report.md              # Token usage, API calls, and cost summary
├── models/
│   ├── __init__.py
│   ├── domain.py                    # Dataclasses: Profile, Request, Event, PaymentOption
│   └── results.py                   # Dataclasses: CandidatePlan, OutputRow, SimulationResult
├── data/
│   ├── __init__.py
│   ├── loader.py                    # CSV parsers, sample exclusion guard, type normalization
│   ├── currency.py                  # Graph-based ExchangeRateConverter with inversion & triangulation
│   ├── linker.py                    # 5-way type-dispatch resolver for linked_event_id
│   └── evidence.py                  # Cache-backed extractor with live Groq fallback
├── simulation/
│   ├── __init__.py
│   ├── recurrence.py                # Detection of fixed day-of-month and integer day-step cadences
│   ├── ledger.py                    # 90-day daily balance timeline simulation
│   └── safety.py                    # Decoupled amount_safe_to_pay & earliest_date_for_full_payment
├── optimizer/
│   ├── __init__.py
│   ├── candidates.py                # Generation of eligible plans with strict installment cap filtering
│   ├── spending.py                  # Combinatorial search over permitted non-protected flexible expenses
│   └── ranker.py                    # 6-tier tie-breaking sorting key
├── explanations/
│   ├── __init__.py
│   ├── templates.py                 # High-fidelity deterministic templates matching benchmark style
│   └── llm.py                       # Groq GPT-OSS 20B generator for multi-change explanations
└── main.py                          # Dual-mode CLI entrypoint
```

---

## 3. Data Ingestion & Evidence Processing

### 3.1 Sample Isolation & User Boundary
- `dataset/requests.csv` contains 250 evaluation requests (`request_26` to `request_275`).
- `dataset/financial_profiles.csv` contains 275 profiles. The first 25 (`user_01` to `user_25`) belong exclusively to `dataset/sample_requests.csv`.
- **Guard**: When running predictions on `requests.csv`, the engine never leaks or processes sample users into the final submission.

### 3.2 Currency Conversion: Graph Triangulation & As-Of Date Matching
- The fixed exchange rate table `dataset/exchange_rates.csv` contains monthly snapshots (dated 15th) for 5 directional pairs: `EUR→USD`, `EUR→ZAR`, `USD→EUR`, `USD→IDR`, `USD→INR`.
- **Rate Inversion**: For missing reverse rates (e.g. `ZAR→EUR`, `IDR→USD`, `INR→USD`), compute $\text{rate} = 1.0 / \text{rate}_{\text{reverse}}$.
- **Triangulation**: For pairs with no direct rate (e.g. `ZAR→IDR` or `INR→EUR`), find the shortest path through base currencies (`USD` or `EUR`) via BFS graph traversal.
- **As-Of Matching**: For transaction date $D$, select the latest rate snapshot where $\text{rate\_date} \le D$ (or the earliest snapshot if $D$ predates the table). Document this explicit assumption in the README.

### 3.3 Linked Event Type-Dispatch (5 Distinct Patterns)
Rather than a naive global deduplication or global retention, `linked_event_id` rows are dispatched by `event_type`:
1. `refund` (22 rows): Real cash reversal of a prior charge. **Keep both** (the original debit and the settled refund credit). Pending refunds remain excluded until settled.
2. `expense` (14 rows): Duplicate representations (e.g., temporary authorization `cancelled` + actual charge `settled`, or duplicate charges). **Collapse into one settled event**.
3. `investment_valuation` (10 rows): Mark-to-market valuations of portfolio holdings. **Exclude entirely** as non-cash, unrealized.
4. `debt_payment` (7 rows): Periodic recurring debt installments. **Keep as distinct real cash payments**.
5. `investment_sale` (5 rows): Cash proceeds realized from sale of an asset. **Keep the sale's cash proceeds credit**, exclude non-cash basis.

### 3.4 Message Fact Extraction & Orphan Linking
- **Orphan Message Resolution**: 76 messages have empty `request_id` and empty `related_event_id`. Join them to the user via `user_id` subject to the defensive temporal guard:
  $$\text{sent\_at} \le \text{request\_date}$$
- **New Job Salary Injection**: 27 messages announce brand-new employment (*"Your first salary will be..."* / *"Gaji pertama..."*). Synthesize a recurring monthly salary credit starting on the stated confirmed credit date.
- **Semantic Classification**:
  - *Salary/Promotion Updates*: Update recurring salary amount from effective date forward (e.g., `user_02` IDR 33,345,000 $\to$ 42,750,000 starting Aug 15).
  - *Unconfirmed / Pending Bonuses*: Explicitly flag as **excluded** until approved and settled.
  - *Unrealized Portfolios / Gig-Economy Unclosed Payouts*: Exclude from available cash.
  - *Seasonal Contract Ended*: Halt recurring income projection beyond end date.
  - *Percentage Adjustments* (e.g., *"Rent increases 12%"*): LLM extracts `+12%`; deterministic Python code applies the arithmetic.
  - *Message + Image Cross-Referencing*: On dual-linked events (e.g. `event_4535` for `user_48`), cross-reference date/status from message and amount from image.

### 3.5 Multimodal Image Extraction
- Exactly 16 events have blank amounts in `financial_events.csv`, mapping 1-to-1 to `dataset/media/images/image_01.png` through `image_16.png`.
- All 16 ground-truth values are stored in `code/cache/image_amounts.json`.
- When `--refresh-cache` is invoked, Groq Qwen 3.6 27B processes each image with strict JSON schema.

---

## 4. Deterministic Simulation Engine

### 4.1 Recurrence Detection
1. **Fixed Calendar Commitments**:
   - Rent, utilities, loans, education, and subscriptions follow constant calendar days of the month. Extrapolate on matching calendar days across $[0, 90]$ days.
2. **Integer Day-Step Variable Spending**:
   - Groceries, transport, and dining follow strict constant integer day-steps ($\Delta d \in \{5, 7, 10, 14, 21\}$ days). Extrapolate from the latest historical event by stepping $\Delta d$ days.
3. **Confirmed Future Inflows**:
   - Count confirmed salaries (from scheduled ledger rows or validated message mutations) on their settlement dates.

### 4.2 90-Day Daily Balance Ledger
For each day $t \in [0, 90]$:
$$\text{Balance}(t) = \text{Balance}(t-1) + \sum \text{Credits}(t) - \sum \text{Debits}(t) - \sum \text{PlanPayments}(t)$$
A plan is **safe** if and only if:
$$\forall t \in [0, 90], \quad \text{Balance}(t) \ge \text{minimum\_balance\_to\_keep}$$

### 4.3 Decoupled `amount_safe_to_pay` & `earliest_date_for_full_payment`
- **Pure Financial Capacity**: `amount_safe_to_pay` answers "what is the maximum cash that could safely leave today without breaching minimum balance over the next 90 days?"
  $$\text{amount\_safe\_to\_pay} = \max\left(0, \min\left(\text{requested\_amount}, \min_{t \in [0, 90]} (\text{Balance}_{\text{baseline}}(t) - \text{minimum\_balance\_to\_keep})\right)\right)$$
  It is **completely decoupled** from the recommended plan's first payment or method.
- `earliest_date_for_full_payment`: First date $D \in [\text{request\_date}, \text{request\_date} + 90]$ where paying `requested_amount` in full keeps all subsequent days above minimum balance without spending changes. Evaluated independently of user payment preferences.

---

## 5. Candidate Optimization & 6-Tier Ranking

### 5.1 Pre-Filtering of Payment Options (Trap Avoidance)
1. **Duration Cap Gate**: Discard any option where option duration exceeds the user's `max_installment_months`. (This eliminates 199 of 515 installment options, or 38.6%, preventing illegal recommendations).
2. **User Consideration Gate**: An option is only considered if its payment method is in `payment_methods_user_will_consider`. If `max_installment_months` is null, installments are completely disqualified.

### 5.2 Candidate Plan Generation
1. **Full Payment**: Safe payment on `request_date` (requires `full_payment` consideration).
2. **Installments**: Filtered options from `request_payment_options.csv`.
3. **Partial Payment**: Exactly 2 payments (`amount_safe_to_pay` on `request_date`, remainder on `earliest_date_for_full_payment`).
   - Allowed only when `allows_partial_payment == true`, user considers `partial_payment`, $0 < \text{amount\_safe\_to\_pay} < \text{requested\_amount}$, and remainder date $\le \text{desired\_completion\_date}$.
4. **Wait**: Single full payment on $\text{earliest\_date\_for\_full\_payment} > \text{request\_date}$ (requires `full_payment` consideration and date $\le \text{desired\_completion\_date}$).
5. **Not Recommended**: Fallback when no safe eligible plan completes the request.

### 5.3 Spending Adjustments
If no candidate plan is safe without spending changes:
- Evaluate combinations of up to 3 non-protected flexible modifications.
- Target `<event_id>` is strictly the **most recent settled historical event** of that series.
- `reduce_to` targets strictly equal `minimum_allowed_amount`.
- Categories in `expense_categories_to_protect` are strictly vetoed.

### 5.4 6-Tier Tie-Breaker
All safe eligible candidate plans are ranked by the sorting key:
$$\text{key} = (\text{violates\_completion\_date}, \text{requires\_spending\_changes}, \text{total\_payable\_amount}, \text{first\_payment\_date}, \text{number\_of\_payments}, \text{payment\_option\_id})$$

---

## 6. Explanations & Output Synthesis

### 6.1 Explanation Generation
- **Standard Deterministic Templates**: Match `sample_requests.csv` patterns for `affordable_now`, `wait`, `installments`, and simple `not_recommended` with zero latency and zero token cost.
- **Hybrid GPT-OSS 20B**: Invoked only for complex multi-spending-change cases, calibrated with few-shot examples.

### 6.2 Output Format
Writes exactly 8 columns to `output.csv` and `dataset/output.csv`:
```text
request_id,amount_safe_to_pay,affordability_status,recommended_payment_method,payment_plan,earliest_date_for_full_payment,spending_changes_needed,decision_explanation
```

---

## 7. CLI Architecture & Run Modes

Entry point: `python code/main.py`
- Default: Evaluates `dataset/requests.csv` and writes `output.csv`.
- `--eval-sample`: Benchmarks the pipeline against all 25 sample requests, verifying 100% agreement on `amount_safe_to_pay`, `affordability_status`, `recommended_payment_method`, and `payment_plan`.
- `--refresh-cache`: Forces live Groq API calls to rebuild evidence caches.

---

## 8. Verification & Calibration Gates
- **Calibration Gate**: 100% match on all 25 sample requests in `dataset/sample_requests.csv`.
- **Validation Gate**: Strict invariant checks on `output.csv` (250 rows, 8 columns, no nulls, non-negative amounts, date ordering).
- **Deliverable Gate**: `code.zip` packaging containing `evaluation/usage_report.md` and complete setup documentation.
