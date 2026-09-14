# Penny Mobile: React Native (Expo) Client

Modern React Native application for **Penny**, an intelligent financial affordability assistant. Built with Expo SDK 57, TypeScript, React Native SVG, and Server-Sent Events (SSE) streaming for real-time multi-agent reasoning.

---

## Features

### 1. 📊 Financial Liquidity Dashboard (`DashboardScreen.tsx`)
- **Real-time Available Balance & Minimum Reserve Buffer**: Hero balance card with active reserve protection health indicator.
- **30-Day Cash Flow Breakdown**: Visualizes confirmed monthly income, fixed burn rate, discretionary surplus, and fixed-cost ratios.
- **Spending Policy Badges**: Displays protected essentials (Rent, Healthcare) and flexible discretionary targets for cutbacks.
- **Upcoming Financial Commitments**: Real-time list of scheduled payroll deposits, rent, and subscription obligations.

### 2. 📈 Interactive 90-Day Cash Flow Trajectory (`TrajectoryScreen.tsx` & `TrajectoryChart.tsx`)
- **Full SVG Vector Charting**: Pure native vector graphics via `react-native-svg` without brittle third-party wrapper dependencies.
- **Safety Invariant Guidelines**: Dashed horizontal threshold displaying the user's inviolable emergency reserve floor.
- **Prospective Purchase Simulator**: Dynamically projects simulated purchases on top of baseline cash flow.
- **Interactive Scrubber Tooltip**: Touch anywhere along the 90-day curve to inspect daily balances and prospective dips.

### 3. 💳 Purchasing Decision & Affordability Optimizer (`AffordabilityScreen.tsx` & `DecisionCardView.tsx`)
- **Fast Decision Verification**: Evaluates prospective purchases against the backend forward simulation engine.
- **Structured Status Badges**:
  - `✅ AFFORDABLE NOW`: Safe to execute immediately without dipping into reserve.
  - `⚠️ AFFORDABLE WITH PLAN`: Requires split installment scheduling to prevent liquidity dips.
  - `⏳ AFFORDABLE LATER`: Projected to become affordable on a future date after upcoming paydays.
  - `🛑 NOT AFFORDABLE`: Exceeds discretionary headroom and violates safety reserves.
- **Multi-Part Installment Schedules & Spending Adjustment Recommendations**.

### 4. 🤖 Agentic Multi-Agent Conversational Brain (`AgentChatScreen.tsx`)
- **Streaming SSE Integration**: Consumes real-time reasoning events (`status`, `token`, `decision_card`, `action_required`, `done`) from FastAPI backend.
- **Embedded Decision Cards**: Financial verdicts render as rich interactive cards directly inside chat bubbles.
- **Human-in-the-Loop Decision Gating (`ApprovalModal.tsx`)**: When Penny proposes spending adjustments (e.g. cutting dining by 50%), execution pauses for explicit user approval before mutations are committed.

---

## Architecture & Monorepo Structure

```
frontend/
├── App.tsx                          # Root container with safe area and tab bar navigation
├── app.json                         # Expo configuration (SDK 57)
├── package.json                     # Dependencies & test scripts
├── tsconfig.json                    # Strict TypeScript configuration
└── src/
    ├── __tests__/                   # Automated tests (api.test.ts)
    ├── components/
    │   ├── ApprovalModal.tsx        # Human-in-the-Loop decision confirmation gate
    │   ├── DecisionCardView.tsx     # Structured affordability verdict card
    │   ├── Header.tsx               # Branding, user identity, and live status badge
    │   ├── MetricCard.tsx           # Reusable KPI card with variant styling
    │   └── TrajectoryChart.tsx      # Interactive 90-day SVG trajectory chart
    ├── screens/
    │   ├── AffordabilityScreen.tsx  # Purchase affordability simulation
    │   ├── AgentChatScreen.tsx      # Streaming multi-agent chat interface
    │   ├── DashboardScreen.tsx      # Liquidity overview and risk breakdown
    │   └── TrajectoryScreen.tsx     # 90-day cash flow forecast and dip inspector
    ├── services/
    │   └── api.ts                   # Strongly typed REST and SSE client with offline fallbacks
    ├── theme/
    │   └── colors.ts                # Fintech dark-mode color tokens
    └── types/
        └── index.ts                 # Full TypeScript contracts matching backend DTOs
```

---

## Getting Started

### Prerequisites
- Node.js >= 20 (Tested on Node v26)
- npm >= 10

### Installation
```bash
cd frontend
npm install
```

### Running the App
```bash
# Start Expo development server
npm start

# Run on Web browser
npm run web

# Run on Android emulator / device
npm run android

# Run on iOS simulator
npm run ios
```

### Running Automated Tests
```bash
npm test
```

### Type Checking
```bash
npm run typecheck
```
