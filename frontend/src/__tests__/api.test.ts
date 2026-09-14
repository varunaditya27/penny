import test from "node:test";
import assert from "node:assert/strict";
import { PennyApiClient } from "../services/api";
import { SSEEvent } from "../types";

test("PennyApiClient fetches user profile correctly with fallback", async () => {
  const client = new PennyApiClient("http://127.0.0.1:9999/api/v1"); // Mock fallback
  const profile = await client.fetchUserProfile("user_01");

  assert.equal(profile.user_id, "user_01");
  assert.equal(profile.home_currency, "USD");
  assert.ok(profile.current_available_balance > 0);
  assert.ok(profile.minimum_balance_to_keep > 0);
  assert.ok(profile.risk_metrics);
  assert.ok(profile.risk_metrics && profile.risk_metrics.monthly_confirmed_income > 0);
  assert.ok(profile.risk_metrics && profile.risk_metrics.monthly_fixed_burn_rate > 0);
});

test("PennyApiClient fetches user financial commitments", async () => {
  const client = new PennyApiClient("http://127.0.0.1:9999/api/v1");
  const events = await client.fetchUserEvents("user_01");

  assert.ok(Array.isArray(events));
  assert.ok(events.length > 0);
  const first = events[0];
  assert.ok(first.event_id);
  assert.ok(first.category);
  assert.ok(typeof first.amount === "number");
});

test("PennyApiClient evaluates purchase affordability with structured plan", async () => {
  const client = new PennyApiClient("http://127.0.0.1:9999/api/v1");
  
  // Safe purchase test
  const smallRes = await client.evaluateAffordability({
    user_id: "user_01",
    requested_amount: 150.0,
    desired_completion_date: "2026-03-31",
    allows_partial_payment: true,
  });
  assert.equal(smallRes.affordability_status, "affordable_now");
  assert.equal(smallRes.amount_safe_to_pay, 150.0);
  assert.ok(smallRes.decision_explanation.length > 10);

  // Large purchase requiring installments test
  const largeRes = await client.evaluateAffordability({
    user_id: "user_01",
    requested_amount: 1200.0,
    desired_completion_date: "2026-03-31",
    allows_partial_payment: true,
  });
  assert.equal(largeRes.affordability_status, "affordable_with_plan");
  assert.equal(largeRes.recommended_payment_method, "installments");
  assert.ok(largeRes.payment_schedule.length > 1);
});

test("PennyApiClient computes 90-day cash flow trajectory points and reserve invariant", async () => {
  const client = new PennyApiClient("http://127.0.0.1:9999/api/v1");
  const traj = await client.fetchCashflowTrajectory("user_01", 300.0, 90);

  assert.equal(traj.user_id, "user_01");
  assert.equal(traj.points.length, 91); // 0 to 90 days inclusive
  assert.ok(traj.minimum_balance_to_keep > 0);
  assert.ok(typeof traj.lowest_projected_balance === "number");
  assert.ok(traj.lowest_balance_date);
  assert.ok(typeof traj.buffer_margin === "number");
  assert.ok(typeof traj.is_safe === "boolean");
});

test("PennyApiClient streams SSE events for conversational reasoning", async () => {
  const client = new PennyApiClient("http://127.0.0.1:9999/api/v1");
  const eventsReceived: SSEEvent[] = [];

  await client.sendChatStream(
    "user_01",
    "Can I afford a $150 jacket today?",
    "test_stream_session",
    (event) => {
      eventsReceived.push(event);
    }
  );

  const eventTypes = eventsReceived.map((e) => e.event);
  assert.ok(eventTypes.includes("status"));
  assert.ok(eventTypes.includes("token"));
  assert.ok(eventTypes.includes("decision_card"));
  assert.ok(eventTypes.includes("done"));
});

test("PennyApiClient handles Human-in-the-Loop approval dispatch", async () => {
  const client = new PennyApiClient("http://127.0.0.1:9999/api/v1");
  
  const approveRes = await client.approveChatAction("user_01", "sess_hitl", "approve");
  assert.equal(approveRes.approval_status, "approved");
  assert.ok(approveRes.response_message.includes("approved"));

  const rejectRes = await client.approveChatAction("user_01", "sess_hitl", "reject");
  assert.equal(rejectRes.approval_status, "rejected");
  assert.ok(rejectRes.response_message.includes("declined"));
});
