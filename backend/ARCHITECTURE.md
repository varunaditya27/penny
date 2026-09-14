<div align="center">

# 🏛️ Buy or Wait? — Architecture & Technical Specification

**End-to-End System Design, Simulation Engine Mechanics, and Financial Safety Invariants**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/architecture-modular%20pipeline-blueviolet.svg)]()
[![Safety Invariant](https://img.shields.io/badge/safety-zero%20balance%20breach-success.svg)]()

[1. Architectural Overview](#1-architectural-overview) •
[2. Domain Entities & Data Contracts](#2-domain-entities--data-contracts) •
[3. Multimodal Evidence Reconciliation](#3-multimodal-evidence-reconciliation) •
[4. Multi-Currency Conversion Graph](#4-multi-currency-conversion-graph) •
[5. Recurrence Engine & Cadence Detection](#5-recurrence-engine--cadence-detection) •
[6. 90-Day Daily Ledger & Safety Invariants](#6-90-day-daily-ledger--safety-invariants) •
[7. Candidate Generation & Search Space](#7-candidate-generation--search-space) •
[8. Two-Tier Spending Modification Optimizer](#8-two-tier-spending-modification-optimizer) •
[9. 6-Tier Lexicographic Plan Ranker](#9-6-tier-lexicographic-plan-ranker) •
[10. Explanation Generation](#10-explanation-generation) •
[11. Modular Agentic Architecture](#11-modular-agentic-architecture) •
[← Return to README](README.md)

</div>

---

> 📘 **Looking for execution instructions, CLI flags, or testing commands?**  
> Refer to the companion developer guide in [`README.md`](./README.md).

---

## 1. Architectural Overview

The **Buy or Wait?** system is designed as a decoupled, multi-stage financial pipeline that determines the affordability of a purchase request over a conservative 90-day forward simulation window.

```mermaid
flowchart TD
    subgraph Ingestion["Stage 1: Ingestion & Reconciliation"]
        A1["Raw CSVs<br/>(profiles, events, requests, options, messages, images)"] --> B1["DataLoader<br/>(backend/core/data/loader.py)"]
        B1 --> C1["EvidenceManager<br/>(backend/core/data/evidence.py)"]
        C1 -->|OCR Cache + Mutations| D1["EventLinker<br/>(backend/core/data/linker.py)"]
        D1 --> E1["ExchangeRateConverter<br/>(backend/core/data/currency.py)"]
    end

    subgraph Analysis["Stage 2: Recurrence & Cash Flow Analysis"]
        E1 --> F1["IncomeStreamClassifier<br/>(backend/core/data/classifier.py)"]
        F1 --> G1["RecurrenceDetector<br/>(backend/core/simulation/recurrence.py)"]
        G1 -->|DOM & Step Streams| H1["DailyLedger Simulation<br/>(backend/core/simulation/ledger.py)"]
        H1 --> I1["SafetyEngine<br/>(backend/core/simulation/safety.py)"]
    end

    subgraph Optimization["Stage 3: Candidate Generation & Optimization"]
        I1 --> J1{"Safe Today?"}
        J1 -->|Yes| K1["CandidateGenerator<br/>(Full Payment Today)"]
        J1 -->|No| L1["CandidateGenerator<br/>(Installments / Partial / Wait)"]
        L1 --> M1{"Viable Plan Found?"}
        M1 -->|No| N1["SpendingOptimizer<br/>(backend/core/optimizer/spending.py)"]
        N1 -->|Tier 1 & Tier 2 Search| O1["Modified Candidates"]
        M1 -->|Yes| P1["Candidate Pool"]
        K1 --> P1
        O1 --> P1
    end

    subgraph Decision["Stage 4: Selection & Explanation"]
        P1 --> Q1["PlanRanker: 6-Tier Lexicographic Sort<br/>(backend/core/optimizer/ranker.py)"]
        Q1 --> R1["Optimal CandidatePlan"]
        R1 --> S1["Explanation Generator<br/>(Deterministic Template / LLM Fallback)"]
        S1 --> T1["OutputRow<br/>(Final 8-Column Contract)"]
    end

    style Ingestion fill:#f8f9fa,stroke:#adb5bd,stroke-width:1px
    style Analysis fill:#e7f5ff,stroke:#339af0,stroke-width:1px
    style Optimization fill:#fff9db,stroke:#fcc419,stroke-width:1px
    style Decision fill:#e6fcf5,stroke:#20c997,stroke-width:1px
```

---

## 2. Domain Entities & Data Contracts

All core domain models are defined as immutable Python dataclasses in [`backend/core/models/domain.py`](./core/models/domain.py) and [`backend/core/models/results.py`](./core/models/results.py).

### Core Dataclasses

```mermaid
classDiagram
    class UserProfile {
        +str user_id
        +str home_currency
        +float current_available_balance
        +float minimum_balance_to_keep
        +List~str~ financial_priorities
        +List~str~ expense_categories_to_protect
        +List~str~ expense_categories_user_is_willing_to_reduce
        +List~str~ expense_categories_user_is_willing_to_stop
        +List~str~ payment_methods_user_will_consider
        +Optional~int~ max_installment_months
        +is_protected(category) bool
        +is_reducible(category) bool
        +is_stoppable(category) bool
        +will_consider(method) bool
    }

    class FinancialEvent {
        +str event_id
        +str user_id
        +str event_type
        +str description
        +str category
        +str direction
        +Optional~float~ amount
        +str currency
        +str event_date
        +Optional~str~ settlement_date
        +str status
        +Optional~str~ linked_event_id
        +str flexibility
        +Optional~float~ minimum_allowed_amount
        +is_debit bool
        +is_credit bool
        +is_cash_flow bool
    }

    class PurchaseRequest {
        +str request_id
        +str user_id
        +str request_date
        +str request_type
        +float requested_amount
        +str desired_completion_date
        +bool allows_partial_payment
        +str request_text
    }

    class PaymentOption {
        +str payment_option_id
        +str request_id
        +str payment_method
        +float payment_amount
        +int number_of_payments
        +str first_payment_date
        +int payment_frequency_days
        +float financing_fee
        +float total_payable_amount
    }

    class CandidatePlan {
        +PaymentMethod payment_method
        +str payment_plan
        +str first_payment_date
        +float total_payable_amount
        +int number_of_payments
        +str spending_changes_needed
        +str payment_option_id
        +bool completes_by_deadline
        +bool requires_spending_changes
        +AffordabilityStatus affordability_status
        +str earliest_date_for_full_payment
        +float amount_safe_to_pay
    }

    UserProfile --> FinancialEvent : possesses
    PurchaseRequest --> UserProfile : belongs to
    PurchaseRequest --> PaymentOption : offers
    CandidatePlan --> PurchaseRequest : resolves
```

---

## 3. Multimodal Evidence Reconciliation

Supporting evidence in `dataset/images.csv` and `dataset/messages.csv` contains untrusted evidence that may confirm missing transaction amounts, announce job promotions, change salary dates, or volunteer subscription cancellations.

[`EvidenceManager`](./data/evidence.py) applies evidence deterministically without allowing prompt injections or external instructions to breach the challenge rules:

1. **Receipt Image Reconciliation**:
   - `images.csv` contains image references (`image_01.png` to `image_25.png`).
   - Where a historical transaction has a missing or null amount (`amount` is blank in `dataset/financial_events.csv`), [`EvidenceManager`](./core/data/evidence.py) extracts the grounded OCR receipt value from [`backend/core/cache/image_amounts.json`](./core/cache/image_amounts.json) and injects the verified amount.
2. **Message Mutation Extraction**:
   - Unstructured messages in `dataset/messages.csv` are parsed for lifecycle events:
     - `STOP_INCOME`: Signals employment termination (`user_05`), halting ongoing recurring payroll projections.
     - `AMEND_SALARY`: Updates baseline compensation following confirmed promotion letters.
     - `AMEND_PAYROLL_DATE`: Overrides the salary calendar day-of-month (`DOM`) to match newly scheduled company payroll dates (e.g. `message_05` moving payday to the 23rd).
     - `CANCEL_SUBSCRIPTION`: Identifies voluntary cancellations announced by the user (e.g. streaming or cloud storage).
     - `NEW_JOB`: Schedules future confirmed employment credits after an onboarding confirmation.

---

## 4. Multi-Currency Conversion Graph

Exchange rates in `dataset/exchange_rates.csv` are dated snapshots on the 15th of each month for direct pairs (`EUR->USD`, `EUR->ZAR`, `USD->EUR`, `USD->IDR`, `USD->INR`). Foreign transactions must be converted into the user's `home_currency`.

[`ExchangeRateConverter`](./data/currency.py) models currencies as a directed graph and dynamically computes rates using Breadth-First Search (BFS) triangulation and mathematical rate inversion.

```mermaid
flowchart LR
    EUR <-->|Direct / Inverted| USD
    EUR -->|Direct| ZAR
    USD -->|Direct| IDR
    USD -->|Direct| INR
    ZAR -.->|Inverted| EUR
    IDR -.->|Inverted| USD
    INR -.->|Inverted| USD

    style EUR fill:#e7f5ff,stroke:#1971c2,stroke-width:2px
    style USD fill:#e7f5ff,stroke:#1971c2,stroke-width:2px
    style ZAR fill:#f8f9fa,stroke:#495057,stroke-width:1px
    style IDR fill:#f8f9fa,stroke:#495057,stroke-width:1px
    style INR fill:#f8f9fa,stroke:#495057,stroke-width:1px
```

### Rate Selection Rules:
1. **As-Of Settlement Date Matching**: Selects the latest snapshot with $\text{rate\_date} \le \text{settlement\_date}$ (or earliest available rate if the event predates the exchange rate table).
2. **Identity**: If $\text{from\_currency} == \text{to\_currency}$, returns $1.0$.
3. **Inversion**: If only $(B \to A)$ is published, rate $(A \to B) = \frac{1.0}{\text{rate}(B \to A)}$.
4. **BFS Triangulation**: If converting between non-direct pairs (e.g. $\text{ZAR} \to \text{INR}$), the converter runs BFS path search: $\text{ZAR} \to \text{EUR} \to \text{USD} \to \text{INR}$, multiplying path edge weights.

---

## 5. Recurrence Engine & Cadence Detection

To forecast future expenses without inventing unsupported patterns, [`RecurrenceDetector`](./simulation/recurrence.py) analyzes settled historical transactions and detects two orthogonal recurrence archetypes:

```mermaid
flowchart TD
    A["Settled Historical Events"] --> B["Cluster by Description & Category"]
    B --> C{"Check Day-of-Month (DOM)<br/>Mode Frequency >= 2"}
    C -->|Yes: Fixed Calendar Day| D["Calendar DOM Stream<br/>(e.g. Rent on 2nd, Utilities on 6th, Salary on 15th)"]
    C -->|No| E{"Check Constant Day-Step<br/>Delta in {5, 7, 10, 14, 21} days"}
    E -->|Yes: Integer Step Cadence| F["Step Cadence Stream<br/>(e.g. Groceries every 10d, Transport every 21d)"]
    E -->|No| G["Irregular / Non-recurring<br/>(Excluded from Recurring Forecast)"]

    style D fill:#d3f9d8,stroke:#2b8a3e,stroke-width:2px
    style F fill:#e7f5ff,stroke:#1971c2,stroke-width:2px
    style G fill:#fff5f5,stroke:#c92a2a,stroke-width:1px
```

### 1. Fixed Calendar Day-of-Month (`DOM`)
- Applied to regular monthly commitments (Rent, Utilities, Subscriptions, Confirmed Salary).
- Extracts statistical mode of day-of-month across historical settled occurrences.
- Projects on day $D$ of each month across the 90-day simulation window.

### 2. Integer Day-Step Cadences (`step`)
- Applied to living expenses occurring at constant interval steps: $\Delta t \in \{5, 7, 10, 14, 21\}$ days.
- Anchors to the most recent historical transaction date and projects subsequent events at intervals of $t_{\text{latest}} + k \cdot \Delta t$.
- Baseline amount is calculated as the **median** of historical settled instances to remain robust against noisy outliers.

---

## 6. 90-Day Daily Ledger & Safety Invariants

The heart of the system is the deterministic [`DailyLedger`](./simulation/ledger.py) simulation engine. It tracks the exact daily balance trajectory:

$$B_t = B_{t-1} + \sum \text{Credits}_t - \sum \text{Debits}_t \quad \text{for } t \in [0, 90]$$

Starting on `request_date` ($t = 0$) with $B_0 = \text{current\_available\_balance}$.

```mermaid
sequenceDiagram
    autonumber
    participant DP as DecisionPipeline
    participant DL as DailyLedger
    participant SE as SafetyEngine

    DP->>DL: Initialize DailyLedger(user, request_date, days=90)
    DL->>DL: Project Recurring Streams (DOM + Step cadences)
    DL->>DL: Subtract Pending Debits on Settlement Dates
    DL->>DL: Add Confirmed Future Salary on Settlement Dates
    DL->>DL: Exclude Unconfirmed Windfalls / Pending Credits
    DL-->>DP: Daily Balance Trajectory B[0..90]

    DP->>SE: compute_safe_amount(ledger, requested_amount)
    SE->>DL: min_headroom() = min(B[t] - minimum_balance_to_keep)
    SE-->>DP: max(0.0, min(requested_amount, min_headroom))

    DP->>SE: find_earliest_full_payment_date(user, streams, req_amt)
    loop Test Candidate Day d in [0..90]
        SE->>DL: Simulate single payment on day d
        DL-->>SE: is_safe() [all B[t] >= minimum_balance_to_keep]
    end
    SE-->>DP: First candidate date where full forecast remains safe
```

### The Three Financial Invariants
1. **The Strict Minimum Balance Invariant**:
   At no point during the 90-day forecast may the balance fall below the user's threshold:
   $$\min_{t \in [0, 90]} B_t \ge \text{minimum\_balance\_to\_keep}$$
2. **Pending Debit Reservation Invariant**:
   All pending debits are reserved and subtracted on their designated settlement dates. Pending credits, refunds, lottery gains, and investment valuations are strictly ignored until settled.
3. **Confirmed Salary Inflow Invariant**:
   Only confirmed ongoing employment salaries are credited on their settlement date. Terminated contracts or unconfirmed gig platform payouts are excluded.

---

## 7. Candidate Generation & Search Space

Given a purchase request, [`CandidateGenerator`](./optimizer/candidates.py) evaluates 4 potential payment methods:

```mermaid
stateDiagram-v2
    [*] --> EvaluateCandidateOptions

    state EvaluateCandidateOptions {
        CheckFullPayment: Test full payment on request_date
        CheckInstallments: Test each merchant installment option
        CheckPartialPayment: Test 2-payment split (safe amount + remainder)
        CheckWait: Test deferred payment on earliest_safe_date
    }

    CheckFullPayment --> CandidatePool: Safe today & completes by deadline
    CheckInstallments --> CandidatePool: Meets max_installment_months & all payments safe
    CheckPartialPayment --> CandidatePool: Allows partial & remainder safe before deadline
    CheckWait --> CandidatePool: Earliest safe date exists within 90 days

    CandidatePool --> PlanRanker: Pass to 6-Tier Lexicographic Ranker
```

1. **Full Payment Today (`full_payment`)**:
   Safe if a single deduction of `requested_amount` on `request_date` maintains $B_t \ge \text{minimum\_balance\_to\_keep}$ for all $t \in [0, 90]$.
2. **Installments (`installments`)**:
   Iterates through options in `request_payment_options.csv`. Rejects options exceeding `user.max_installment_months`. Simulates all recurring installment dates and verifies balance remains $\ge \text{minimum\_balance\_to\_keep}$ throughout.
3. **Partial Payment (`partial_payment`)**:
   Generated only when:
   - `request.allows_partial_payment == True`
   - `user.will_consider("partial_payment") == True`
   - $0 < \text{amount\_safe\_to\_pay} < \text{requested\_amount}$
   - The second payment ($\text{requested\_amount} - \text{amount\_safe\_to\_pay}$) is scheduled on `earliest_date_for_full_payment` on or before `desired_completion_date`.
4. **Deferred Payment (`wait`)**:
   Schedules a single full payment on `earliest_date_for_full_payment` (the first date where post-inflow cashflow keeps the entire subsequent forecast safe).

---

## 8. Two-Tier Spending Modification Optimizer

If no candidate plan is safe without modifications, [`SpendingOptimizer`](./optimizer/spending.py) executes a targeted combinatorial search across flexible non-protected expenses:

```mermaid
flowchart TD
    A["Candidate Search Shortfall"] --> B{"User permitted stoppable<br/>or reducible categories?"}
    B -->|No| C["Reject: not_affordable / not_recommended"]
    B -->|Yes| D["Tier 1 Search: Volunteered Modifications<br/>(Categories explicitly user-volunteered)"]
    D --> E{"Viable Plan Found with <= 3 changes?"}
    E -->|Yes| F["Select Minimal Tier 1 Modification Plan"]
    E -->|No| G["Tier 2 Search: Broader Flexible Expenses<br/>(Other non-protected discretionary streams)"]
    G --> H{"Viable Plan Found with <= 3 changes?"}
    H -->|Yes| I["Select Minimal Tier 2 Modification Plan"]
    H -->|No| C

    style D fill:#e7f5ff,stroke:#1971c2,stroke-width:2px
    style G fill:#fff9db,stroke:#fcc419,stroke-width:2px
    style F fill:#d3f9d8,stroke:#2b8a3e,stroke-width:2px
    style I fill:#d3f9d8,stroke:#2b8a3e,stroke-width:2px
    style C fill:#fff5f5,stroke:#c92a2a,stroke-width:1px
```

### Search Constraints:
- **Maximum 3 modifications**: At most three `stop:<event_id>` or `reduce_to:<event_id>:<amount>` actions.
- **Strict Protection Invariant**: Categories in `expense_categories_to_protect` (e.g. rent, groceries) are strictly forbidden from modification.
- **Minimum Allowed Floor**: When reducing an event, the new amount cannot fall below `event.minimum_allowed_amount`.

---

## 9. 6-Tier Lexicographic Plan Ranker

When multiple candidate plans are financially viable, [`PlanRanker`](./optimizer/ranker.py) applies a strict 6-tier lexicographic tie-breaking hierarchy to select the optimal plan:

```mermaid
graph TD
    T1["Tier 1: Completes by Deadline<br/>(completes_by_deadline == True > False)"]
    T2["Tier 2: Avoids Spending Modifications<br/>(requires_spending_changes == False > True)"]
    T3["Tier 3: Minimizes Total Payment Outflow<br/>(total_payable_amount ASC)"]
    T4["Tier 4: Starts Earlier<br/>(first_payment_date ASC)"]
    T5["Tier 5: Fewer Payments<br/>(number_of_payments ASC)"]
    T6["Tier 6: Preserves Provider Option Ordering<br/>(original payment_option_id order)"]

    T1 --> T2 --> T3 --> T4 --> T5 --> T6

    style T1 fill:#e7f5ff,stroke:#1971c2,stroke-width:2px
    style T2 fill:#e7f5ff,stroke:#1971c2,stroke-width:2px
    style T3 fill:#e6fcf5,stroke:#0ca678,stroke-width:2px
    style T4 fill:#e6fcf5,stroke:#0ca678,stroke-width:2px
    style T5 fill:#fff9db,stroke:#fcc419,stroke-width:2px
    style T6 fill:#f8f9fa,stroke:#495057,stroke-width:1px
```

---

## 10. Explanation Generation

The final recommendation is explained through concise, grounded natural language:
- **Deterministic Synthesizer ([`ExplanationTemplateSynthesizer`](./explanations/templates.py))**:
  Formats verified sentences directly matching the benchmark style (e.g. `"Pay EUR 600 today. This leaves at least EUR 800 available over the next 90 days."`).
- **LLM Generator ([`LLMExplanationGenerator`](./explanations/llm.py))**:
  When `GROQ_API_KEY` is configured, calls Groq API (`openai/gpt-oss-20b`) with few-shot calibration. If unconfigured or encountering network latency, it seamlessly and gracefully falls back to the deterministic template without interrupting execution.

---

## 11. Modular Agentic Architecture

The conversational financial assistant is engineered using **LangGraph** with a strict **single-responsibility modular architecture** to avoid file bloat. No single file contains multiple concerns:

```mermaid
graph TD
    User["User Query / SSE Request"] --> Router["Chat Router<br/>(backend/app/api/v1/chat/router.py)"]
    Router --> Events["SSE Event Stream<br/>(backend/app/api/v1/chat/events.py)"]
    Events --> Graph["Compiled StateGraph<br/>(backend/app/agent/graph.py)"]

    subgraph StateGraph["LangGraph State Workflow"]
        AgentNode["Agent Node<br/>(nodes/agent.py)"]
        ToolsNode["Tools Node<br/>(nodes/tools.py)"]
        ApprovalNode["Approval Node (HitL)<br/>(nodes/approval.py)"]
        Routing["Conditional Edges<br/>(edges/routing.py)"]
        Checkpointer["Memory Checkpointer<br/>(checkpointers/memory.py)"]
    end

    Graph --> AgentNode
    AgentNode --> Routing
    Routing -->|Tool Call| ToolsNode
    Routing -->|Mutation Needs Approval| ApprovalNode
    Routing -->|Complete| Events
    ToolsNode --> Routing
    ApprovalNode --> Routing

    subgraph ToolModules["Modular Financial Tools (Single Responsibility)"]
        EvalTool["evaluation.py<br/>(evaluate_purchase)"]
        TrajTool["trajectory.py<br/>(get_cashflow_trajectory)"]
        ProfTool["profile.py<br/>(get_user_financial_profile)"]
        SpendTool["spending.py<br/>(simulate_spending_reduction / approval)"]
    end

    ToolsNode --> ToolModules
```

### Module Responsibilities:
1. **`state.py`**: Declares `AgentState` schema, message reducer, decision cards, and pending approval structures.
2. **`prompts/`**:
   - `system.py`: Penny assistant persona, 90-day simulation rules, safety floor enforcement.
   - `templates.py`: Human-in-the-loop spending approval and decision summary templates.
3. **`tools/`**:
   - `evaluation.py`: Connects purchase evaluation to `FinanceService`.
   - `trajectory.py`: Simulates 90-day trajectory with `SimulationService`.
   - `profile.py`: Retrieves user preferences, budgets, and cash flow risk metrics.
   - `spending.py`: Simulates category reductions and triggers approval requests.
   - `factory.py`: Unified dependency-injected tool registry.
4. **`nodes/`**:
   - `agent.py`: Tool-bound model invocation with graceful deterministic fallback.
   - `tools.py`: Executes tool calls and updates structured state (`decision_card`, `pending_action`).
   - `approval.py`: Evaluates human approval responses for budget alterations.
5. **`edges/`**:
   - `routing.py`: Pure routing logic between agent, tools, approval gate, and END.
6. **`checkpointers/`**:
   - `memory.py`: In-memory multi-turn conversational checkpointing per session ID.
7. **`api/v1/chat/`**:
   - `events.py`: Formats W3C standard SSE lines and coordinates async event stream.
   - `router.py`: FastAPI endpoints for `POST /api/v1/chat/stream` and `POST /api/v1/chat/approve`.

---

<div align="center">

<hr />

**HackerRank Orchestrate (September 2026) — Buy or Wait?**  
*Review developer commands, CLI flags, and test suite: [Developer Guide (README.md) ➔](README.md)*

</div>

