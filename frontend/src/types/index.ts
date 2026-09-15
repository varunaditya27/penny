export interface CashFlowRiskMetrics {
  monthly_fixed_burn_rate: number;
  monthly_confirmed_income: number;
  fixed_cost_ratio: number;
  discretionary_cashflow: number;
}

export interface UserProfile {
  user_id: string;
  home_currency: string;
  current_available_balance: number;
  minimum_balance_to_keep: number;
  financial_priorities: string[];
  expense_categories_to_protect: string[];
  expense_categories_to_reduce: string[];
  expense_categories_to_stop: string[];
  payment_methods_user_will_consider: string[];
  max_installment_months?: number;
  risk_metrics?: CashFlowRiskMetrics;
}

export interface FinancialEvent {
  event_id: string;
  user_id: string;
  event_date: string;
  event_type: 'income' | 'expense' | 'recurring_income' | 'recurring_expense' | 'subscription';
  category: string;
  amount: number;
  currency: string;
  description: string;
  is_recurring: boolean;
  recurrence_cadence_days?: number;
  confidence_score?: number;
}

export interface PaymentScheduleItem {
  date: string;
  amount: number;
}

export interface SpendingChangeItem {
  action: 'stop' | 'reduce_to';
  event_id: string;
  amount?: number;
}

export interface AffordabilityRequest {
  user_id: string;
  requested_amount: number;
  desired_completion_date: string;
  request_date?: string;
  allows_partial_payment?: boolean;
  request_text?: string;
  request_id?: string;
}

export type AffordabilityStatus =
  | 'affordable_now'
  | 'affordable_with_plan'
  | 'affordable_later'
  | 'not_affordable';

export interface AffordabilityResponse {
  request_id: string;
  user_id: string;
  amount_safe_to_pay: number;
  affordability_status: AffordabilityStatus;
  recommended_payment_method: string;
  payment_schedule: PaymentScheduleItem[];
  earliest_date_for_full_payment?: string | null;
  spending_changes: SpendingChangeItem[];
  decision_explanation: string;
}

export interface TrajectoryPoint {
  date: string;
  baseline_balance: number;
  with_purchase_balance?: number | null;
}

export interface TrajectoryResponse {
  user_id: string;
  currency: string;
  minimum_balance_to_keep: number;
  points: TrajectoryPoint[];
  lowest_projected_balance: number;
  lowest_balance_date: string;
  buffer_margin: number;
  is_safe: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'human' | 'assistant';
  content: string;
  decisionCard?: AffordabilityResponse | null;
  timestamp: string;
  pendingApproval?: {
    action_type: string;
    action_description: string;
    proposed_changes: string[];
    estimated_monthly_savings: number;
  } | null;
}

export interface SSEEvent {
  event: 'status' | 'token' | 'decision_card' | 'trajectory_preview' | 'action_required' | 'approval_required' | 'done' | 'error';
  data: any;
}
