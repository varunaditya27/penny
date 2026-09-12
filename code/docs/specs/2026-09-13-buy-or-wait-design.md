# Design Specification: Buy or Wait? Financial Decision Agent

**Challenge**: HackerRank Orchestrate (September 2026) — *Buy or Wait?*  
**Date**: September 13, 2026  
**Status**: Approved Specification  
**Authors**: Antigravity & Engineering Team

---

## 1. Executive Summary & Architectural Vision

The **Buy or Wait?** system is an AI-powered financial decision agent designed to evaluate purchase and expense requests (`dataset/requests.csv`). It recommends whether a user should pay in full today, pay partially, take an installment option, wait for a future safe date, or not proceed.

### Core Architectural Demarcation
To prioritize **simplicity, reliability, and determinism**, the system divides responsibilities strictly:
1. **Deterministic Core (100% Python)**:
   - Reconstructs financial profiles, parses dated currency conversions, detects recurring cash flows (fixed calendar and integer day-step cadences), simulates daily balance trajectories over 90 days, computes `amount_safe_to_pay` and `earliest_date_for_full_payment`, evaluates candidate plans, and ranks options using a strict 6-tier tie-breaker.
2. **Targeted Groq LLM Integration (Multimodal & Semantic)**:
   - **Qwen 3.6 27B Vision**: Extracts missing numerical amounts from receipts/payslips (`dataset/media/images/*.png`), cached in `code/cache/image_amounts.json`.
   - **Meta LLaMA 3.3 70B**: Extracts structured mutations (`CONFIRM_SALARY`, `CANCEL_EVENT`, `ADJUST_RECURRING_AMOUNT`) from 215 multilingual messages (`dataset/messages.csv`), cached in `code/cache/message_mutations.json`.
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
│   └── specs/
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
│   ├── loader.py                    # CSV parsers and type normalization
│   ├── currency.py                  # ExchangeRateConverter with date/currency pair lookup
│   └── evidence.py                  # Cache-backed extractor with live Groq fallback
├── simulation/
│   ├── __init__.py
│   ├── recurrence.py                # Detection of fixed day-of-month and integer day-step cadences
│   ├── ledger.py                    # 90-day daily balance timeline simulation
│   └── safety.py                    # amount_safe_to_pay & earliest_date_for_full_payment calculations
├── optimizer/
│   ├── __init__.py
│   ├── candidates.py                # Generation of eligible full, partial, installment, and wait plans
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

### 3.1 Currency Conversion
- All balances, requests, and outputs are denominated in the user's `home_currency`.
- For foreign-currency cash events, the `ExchangeRateConverter` looks up `(rate_date, from_currency, to_currency)` from `dataset/exchange_rates.csv`.
- Rate calculation: $\text{amount}_{\text{home}} = \text{amount}_{\text{foreign}} \times \text{rate}$.

### 3.2 Multimodal Image Extraction
- Exactly 16 events have blank amounts in `financial_events.csv`.
- Extracted values are loaded from `code/cache/image_amounts.json`.
- If cache is refreshed via `--refresh-cache`, Groq Qwen 3.6 27B processes the base64-encoded image with strict JSON schema `{"amount": float, "currency": str}`.

### 3.3 Message Mutation Extraction
- Messages in `dataset/messages.csv` contain untrusted text in English and Indonesian.
- LLaMA 3.3 70B extracts typed mutations:
  ```json
  {
    "mutation_type": "CONFIRM_SALARY | CANCEL_EVENT | ADJUST_RECURRING_AMOUNT | IGNORE",
    "effective_date": "YYYY-MM-DD",
    "new_amount": float,
    "confidence": float
  }
  ```
- Mutations are stored in `code/cache/message_mutations.json`. Any instructions attempting to override challenge rules (prompt injections) map to `IGNORE`.

---

## 4. Deterministic Simulation Engine

### 4.1 Recurrence Detection
1. **Fixed Calendar Commitments**:
   - Groups settled transactions by description and category.
   - If day-of-month is constant ($\ge 2$ occurrences), project forward on that calendar day across the 90-day window $[\text{request\_date}, \text{request\_date} + 90]$.
2. **Integer Day-Step Variable Spending**:
   - If successive transaction dates have constant day difference $\Delta d \in \{5, 7, 10, 14, 21\}$, project forward from the last historical occurrence by stepping $\Delta d$ days.
   - Baseline amount is the conservative historical average or last occurrence.
3. **Confirmed Salaries & Scheduled Debits**:
   - Only count confirmed salary credits on their settlement dates (from scheduled events or confirmed employer messages).
   - Reserve all pending debits on their settlement dates. Ignore pending credits.

### 4.2 90-Day Daily Balance Ledger
For each day $t \in [0, 90]$:
$$\text{Balance}(t) = \text{Balance}(t-1) + \sum \text{Credits}(t) - \sum \text{Debits}(t) - \sum \text{PlanPayments}(t)$$
A plan is **safe** if and only if:
$$\forall t \in [0, 90], \quad \text{Balance}(t) \ge \text{minimum\_balance\_to\_keep}$$

### 4.3 Safe Amount & Earliest Full Payment Date
- `amount_safe_to_pay`:
  $$\text{amount\_safe\_to\_pay} = \max\left(0, \min\left(\text{requested\_amount}, \min_{t \in [0, 90]} (\text{Balance}_{\text{baseline}}(t) - \text{minimum\_balance\_to\_keep})\right)\right)$$
- `earliest_date_for_full_payment`:
  First date $D \in [\text{request\_date}, \text{request\_date} + 90]$ where paying `requested_amount` in full on date $D$ keeps all future days $\ge \text{minimum\_balance\_to\_keep}$ without spending changes. If no such date exists, it is empty `""`.

---

## 5. Candidate Optimization & 6-Tier Ranking

### 5.1 Candidate Generation
1. **Full Payment**: Safe single payment on `request_date`. Requires `full_payment` in `payment_methods_user_will_consider`.
2. **Installments**: Candidate plans matching eligible options from `dataset/request_payment_options.csv`. Disqualified if user rejects `installments` or if option duration exceeds `max_installment_months`.
3. **Partial Payment**: Exactly 2 payments (`amount_safe_to_pay` on `request_date`, remainder on `earliest_date_for_full_payment`). Eligible only when:
   - `allows_partial_payment == true`
   - User considers `partial_payment`
   - $0 < \text{amount\_safe\_to\_pay} < \text{requested\_amount}$
   - $\text{earliest\_date\_for\_full\_payment} \le \text{desired\_completion\_date}$
4. **Wait**: Single full payment on $\text{earliest\_date\_for\_full\_payment} > \text{request\_date}$. Eligible only when user considers `full_payment` and $\text{earliest\_date\_for\_full\_payment} \le \text{desired\_completion\_date}$.
5. **Not Recommended**: Fallback when no safe option completes the request.

### 5.2 Spending Adjustments
If no candidate plan is safe without changes, evaluate combinations of $k \in \{1, 2, 3\}$ changes:
- `stop:<event_id>`: Eliminates recurring expense (requires `stoppable` and category in `expense_categories_user_is_willing_to_stop`).
- `reduce_to:<event_id>:<min_amount>`: Reduces expense to `minimum_allowed_amount` (requires `reducible` and category in `expense_categories_user_is_willing_to_reduce`).
- Target `<event_id>` is strictly the **most recent settled historical event** of that stream.
- Protected categories in `expense_categories_to_protect` can never be altered.

### 5.3 6-Tier Tie-Breaker
All safe eligible candidate plans are ranked by the sorting key:
$$\text{key} = (\text{violates\_completion\_date}, \text{requires\_spending\_changes}, \text{total\_payable\_amount}, \text{first\_payment\_date}, \text{number\_of\_payments}, \text{payment\_option\_id})$$

---

## 6. Explanations & Output Synthesis

### 6.1 Explanation Generation
- **Standard Templates**: Deterministic templates for `affordable_now`, `wait`, `installments`, and simple `not_recommended` matching `sample_requests.csv` ground truth.
- **Hybrid GPT-OSS 20B**: Used when recommendations involve spending reductions or compound reasons, synthesizing concise, grounded text.

### 6.2 Output Format
Writes exactly 8 columns to `output.csv` and `dataset/output.csv`:
```text
request_id,amount_safe_to_pay,affordability_status,recommended_payment_method,payment_plan,earliest_date_for_full_payment,spending_changes_needed,decision_explanation
```

---

## 7. CLI Architecture & Run Modes

Entry point: `python code/main.py`
- Default: Processes `dataset/requests.csv` and writes `output.csv`.
- `--eval-sample`: Evaluates system against `dataset/sample_requests.csv`, reporting accuracy, exact matches, and diffs.
- `--refresh-cache`: Forces live Groq API calls to rebuild multimodal and message mutation caches.

---

## 8. Verification & Calibration Gates
- **Gate 1**: 100% match on all 25 sample requests in `dataset/sample_requests.csv`.
- **Gate 2**: Schema validation on `output.csv` (250 rows, 8 columns, exact allowed values, valid dates, non-negative amounts).
- **Gate 3**: `code.zip` packaging verification and `code/evaluation/usage_report.md` generation.
