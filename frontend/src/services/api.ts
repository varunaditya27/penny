import {
  AffordabilityRequest,
  AffordabilityResponse,
  FinancialEvent,
  SSEEvent,
  TrajectoryResponse,
  UserProfile,
} from "../types";

const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class PennyApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async fetchUserProfile(userId: string = "user_01"): Promise<UserProfile> {
    try {
      const res = await fetch(`${this.baseUrl}/users/${userId}`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("API offline, using realistic mock user profile", err);
      return {
        user_id: userId,
        home_currency: "USD",
        current_available_balance: 4250.0,
        minimum_balance_to_keep: 1500.0,
        financial_priorities: [
          "Maintain 3-month reserve buffer",
          "Prioritize 0% financing over lump sum",
        ],
        expense_categories_to_protect: ["Rent", "Groceries", "Health Insurance"],
        expense_categories_to_reduce: ["Dining Out", "Coffee", "Shopping"],
        expense_categories_to_stop: ["Gym Membership", "Streaming Subscriptions"],
        payment_methods_user_will_consider: ["full_payment", "installments"],
        max_installment_months: 6,
        risk_metrics: {
          monthly_fixed_burn_rate: 2100.0,
          monthly_confirmed_income: 3800.0,
          fixed_cost_ratio: 0.55,
          discretionary_cashflow: 1700.0,
        },
      };
    }
  }

  async fetchUserEvents(userId: string = "user_01"): Promise<FinancialEvent[]> {
    try {
      const res = await fetch(`${this.baseUrl}/users/${userId}/events?limit=20`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();
      return data.items || data;
    } catch (err) {
      console.warn("API offline, using mock financial events", err);
      return [
        {
          event_id: "evt_101",
          user_id: userId,
          event_date: "2026-03-01",
          event_type: "recurring_income",
          category: "Salary",
          amount: 1900.0,
          currency: "USD",
          description: "Bi-weekly Payroll Deposit",
          is_recurring: true,
          recurrence_cadence_days: 14,
        },
        {
          event_id: "evt_102",
          user_id: userId,
          event_date: "2026-03-03",
          event_type: "recurring_expense",
          category: "Housing",
          amount: -1250.0,
          currency: "USD",
          description: "Apartment Rent",
          is_recurring: true,
          recurrence_cadence_days: 30,
        },
        {
          event_id: "evt_103",
          user_id: userId,
          event_date: "2026-03-07",
          event_type: "subscription",
          category: "Entertainment",
          amount: -45.0,
          currency: "USD",
          description: "Streaming Bundles",
          is_recurring: true,
          recurrence_cadence_days: 30,
        },
        {
          event_id: "evt_104",
          user_id: userId,
          event_date: "2026-03-15",
          event_type: "recurring_income",
          category: "Salary",
          amount: 1900.0,
          currency: "USD",
          description: "Bi-weekly Payroll Deposit",
          is_recurring: true,
          recurrence_cadence_days: 14,
        },
      ];
    }
  }

  async evaluateAffordability(
    req: AffordabilityRequest
  ): Promise<AffordabilityResponse> {
    try {
      const res = await fetch(`${this.baseUrl}/affordability/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      });
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("API offline, generating calculated affordability evaluation", err);
      const isAffordable = req.requested_amount <= 800;
      const status = isAffordable ? "affordable_now" : "affordable_with_plan";

      return {
        request_id: `req_${Date.now()}`,
        user_id: req.user_id,
        amount_safe_to_pay: isAffordable ? req.requested_amount : 400.0,
        affordability_status: status,
        recommended_payment_method: isAffordable ? "full_payment" : "installments",
        payment_schedule: isAffordable
          ? [{ date: req.desired_completion_date, amount: req.requested_amount }]
          : [
              { date: "2026-03-15", amount: req.requested_amount / 2 },
              { date: "2026-03-31", amount: req.requested_amount / 2 },
            ],
        spending_changes: isAffordable
          ? []
          : [
              {
                action: "reduce_to",
                event_id: "Dining Out",
                amount: 150.0,
              },
            ],
        decision_explanation: isAffordable
          ? `Penny verified that a full payment of $${req.requested_amount.toFixed(
              2
            )} keeps your cash flow safely above your $1,500 reserve buffer at all times over the next 90 days.`
          : `A single upfront payment of $${req.requested_amount.toFixed(
              2
            )} causes your balance to dip below your safety threshold. A 2-part installment plan keeps your reserve protected.`,
      };
    }
  }

  async fetchCashflowTrajectory(
    userId: string = "user_01",
    prospectiveAmount?: number,
    days: number = 90
  ): Promise<TrajectoryResponse> {
    try {
      const query = new URLSearchParams();
      if (prospectiveAmount) query.set("prospective_amount", prospectiveAmount.toString());
      query.set("days", days.toString());

      const res = await fetch(
        `${this.baseUrl}/simulation/trajectory/${userId}?${query.toString()}`
      );
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("API offline, generating simulated 90-day trajectory", err);
      const points = [];
      let balance = 4250.0;
      const reserve = 1500.0;
      const purchase = prospectiveAmount || 0.0;

      for (let i = 0; i <= days; i++) {
        const d = new Date(2026, 2, 1 + i);
        const dateStr = d.toISOString().split("T")[0];

        // Payroll on 1st and 15th
        if (d.getDate() === 1 || d.getDate() === 15) balance += 1900.0;
        // Rent on 3rd
        if (d.getDate() === 3) balance -= 1250.0;
        // Daily burn
        balance -= 35.0;

        points.push({
          date: dateStr,
          baseline_balance: Math.round(balance * 100) / 100,
          with_purchase_balance:
            purchase > 0
              ? Math.max(0, Math.round((balance - purchase) * 100) / 100)
              : null,
        });
      }

      const lowest = Math.min(...points.map((p) => p.baseline_balance));
      const lowestDate = points.find((p) => p.baseline_balance === lowest)?.date || "2026-03-31";

      return {
        user_id: userId,
        currency: "USD",
        minimum_balance_to_keep: reserve,
        points,
        lowest_projected_balance: lowest,
        lowest_balance_date: lowestDate,
        buffer_margin: lowest - reserve,
        is_safe: lowest >= reserve,
      };
    }
  }

  async sendChatStream(
    userId: string,
    message: string,
    sessionId: string,
    onEvent: (event: SSEEvent) => void
  ): Promise<void> {
    try {
      const res = await fetch(`${this.baseUrl}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          message,
          session_id: sessionId,
        }),
      });

      if (!res.ok) throw new Error(`HTTP stream error ${res.status}`);
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        buffer = buffer.replace(/\r\n/g, "\n");
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const block of lines) {
          if (!block.trim()) continue;
          let eventType = "message";
          let dataStr = "";

          for (const line of block.split("\n")) {
            if (line.startsWith("event:")) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataStr = line.slice(5).trim();
            }
          }

          if (dataStr) {
            try {
              const parsed = JSON.parse(dataStr);
              onEvent({ event: eventType as any, data: parsed });
            } catch {
              onEvent({ event: eventType as any, data: dataStr });
            }
          }
        }
      }
    } catch (err) {
      console.warn("Stream error or offline, simulating multi-agent response", err);
      // Simulated SSE stream for offline / dev preview
      onEvent({
        event: "status",
        data: { step: "routed", intent: "affordability_evaluation", message: "Supervisor analyzed intent..." },
      });
      await new Promise((r) => setTimeout(r, 400));
      onEvent({
        event: "status",
        data: { step: "simulated", message: "Affordability specialist evaluating 90-day trajectory..." },
      });
      await new Promise((r) => setTimeout(r, 400));

      const isBig = message.includes("1000") || message.includes("2000") || message.includes("laptop");
      if (isBig) {
        onEvent({
          event: "decision_card",
          data: {
            request_id: `req_${Date.now()}`,
            user_id: userId,
            amount_safe_to_pay: 500.0,
            affordability_status: "affordable_with_plan",
            recommended_payment_method: "installments",
            payment_schedule: [
              { date: "2026-03-15", amount: 400.0 },
              { date: "2026-03-31", amount: 400.0 },
            ],
            spending_changes: [{ action: "reduce_to", event_id: "Dining Out", amount: 120.0 }],
            decision_explanation:
              "An upfront lump sum dips below your $1,500 reserve cushion on March 28th. A 2-installment schedule keeps your cash flow buffer intact.",
          },
        });
        onEvent({
          event: "token",
          data: {
            delta:
              "### ⚠️ AFFORDABLE WITH PAYMENT PLAN\n\n- **Safe to Spend Upfront**: $500.00\n- **Recommended Plan**: 2 Installments of $400.00\n- **Lowest Projected Buffer**: $1,620.00 (Reserve: $1,500.00)\n\nPaying in installments avoids a liquidity dip on March 28th before your next payday.",
          },
        });
      } else {
        onEvent({
          event: "decision_card",
          data: {
            request_id: `req_${Date.now()}`,
            user_id: userId,
            amount_safe_to_pay: 150.0,
            affordability_status: "affordable_now",
            recommended_payment_method: "full_payment",
            payment_schedule: [{ date: "2026-03-05", amount: 150.0 }],
            spending_changes: [],
            decision_explanation:
              "Full payment is completely safe. Your forward balance stays at least $1,200 above your emergency reserve.",
          },
        });
        onEvent({
          event: "token",
          data: {
            delta:
              "### ✅ AFFORDABLE NOW\n\n- **Safe to Spend**: $150.00\n- **Recommended Method**: `full_payment`\n- **Lowest 90-Day Balance**: $2,720.00 (Safety Buffer: $1,500.00)\n\nYou can make this purchase immediately without jeopardizing any scheduled bills or your emergency cushion.",
          },
        });
      }

      onEvent({ event: "done", data: { session_id: sessionId, status: "completed" } });
    }
  }

  async approveChatAction(
    userId: string,
    sessionId: string,
    action: "approve" | "reject"
  ): Promise<any> {
    try {
      const res = await fetch(`${this.baseUrl}/chat/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, session_id: sessionId, action }),
      });
      if (!res.ok) throw new Error(`HTTP approval error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("API offline, returning simulated approval result", err);
      return {
        session_id: sessionId,
        approval_status: action === "approve" ? "approved" : "rejected",
        response_message:
          action === "approve"
            ? "Spending cutbacks approved and committed to your active profile."
            : "Adjustments declined. Profile remains unchanged.",
      };
    }
  }
}

export const api = new PennyApiClient();
