import itertools
import logging
from typing import List, Optional, Tuple

from code.models.domain import PaymentOption, PurchaseRequest, UserProfile
from code.models.results import AffordabilityStatus, CandidatePlan, PaymentMethod
from code.optimizer.candidates import CandidateGenerator, format_plan_amount
from code.optimizer.ranker import PlanRanker
from code.simulation.ledger import DailyLedger
from code.simulation.recurrence import RecurringStream

logger = logging.getLogger("buy_or_wait.optimizer.spending")


class SpendingOptimizer:
    """
    Optimizes spending reductions and cancellations for users when baseline funds are insufficient.
    Evaluates subsets of up to 3 non-protected modifications (stop:<event_id> and reduce_to:<event_id>:<min_amount>).
    Strictly obeys user profile category permissions and event flexibility tags.
    """

    @classmethod
    def get_eligible_modifications(
        cls, user: UserProfile, recurring_streams: List[RecurringStream]
    ) -> List[Tuple[str, str, Optional[float], str]]:
        """
        Returns list of eligible atomic modifications:
        Tuple of (action, event_id, target_amount, category).
        action is 'stop' or 'reduce_to'.
        """
        mods_with_date: List[Tuple[str, str, Optional[float], str, str]] = []
        seen_keys = set()

        for stream in recurring_streams:
            if stream.is_credit:
                continue

            cat = stream.category
            ev_id = stream.latest_event_id

            # Rule 1: Protected categories cannot be modified
            if user.is_category_protected(cat):
                continue

            # Rule 2: Check stoppable
            if user.can_stop_category(cat) and stream.flexibility in ["stoppable", "reducible_or_stoppable"]:
                key = ("stop", ev_id)
                if key not in seen_keys:
                    seen_keys.add(key)
                    mods_with_date.append(("stop", ev_id, None, cat, stream.latest_date))

            # Rule 3: Check reducible
            if (
                user.can_reduce_category(cat)
                and stream.flexibility in ["reducible", "reducible_or_stoppable"]
                and stream.minimum_allowed_amount is not None
            ):
                key = ("reduce_to", ev_id, stream.minimum_allowed_amount)
                if key not in seen_keys:
                    seen_keys.add(key)
                    mods_with_date.append(("reduce_to", ev_id, stream.minimum_allowed_amount, cat, stream.latest_date))

        # Sort newer records first per challenge conflict resolution rules (§6.3)
        mods_with_date.sort(key=lambda x: x[4], reverse=True)
        return [(m[0], m[1], m[2], m[3]) for m in mods_with_date]

    @classmethod
    def format_modifications_string(
        cls, mod_combo: Tuple[Tuple[str, str, Optional[float], str], ...]
    ) -> str:
        parts: List[str] = []
        for action, ev_id, min_amt, _ in mod_combo:
            if action == "stop":
                parts.append(f"stop:{ev_id}")
            elif action == "reduce_to" and min_amt is not None:
                parts.append(f"reduce_to:{ev_id}:{format_plan_amount(min_amt)}")
        return "|".join(parts)

    @classmethod
    def search_spending_plans(
        cls,
        user: UserProfile,
        request: PurchaseRequest,
        recurring_streams: List[RecurringStream],
        future_events: list,
        options: List[PaymentOption],
        safe_amt_baseline: float,
        earliest_full_date: str,
        max_modifications: int = 3,
    ) -> List[CandidatePlan]:
        """
        Combinatorially searches subsets of size 1, 2, ..., max_modifications.
        For each valid subset, evaluates candidate payment plans under the modified budget.
        Returns all plans that successfully complete by desired_completion_date.
        """
        eligible_mods = cls.get_eligible_modifications(user, recurring_streams)
        if not eligible_mods:
            return []

        successful_plans: List[CandidatePlan] = []

        # Search by subset size: smaller subsets (fewer sacrifices) preferred
        for k in range(1, min(max_modifications, len(eligible_mods)) + 1):
            k_level_plans: List[CandidatePlan] = []

            for combo in itertools.combinations(eligible_mods, k):
                # Ensure mutual exclusivity: cannot stop and reduce the same event
                event_ids = [m[1] for m in combo]
                if len(event_ids) != len(set(event_ids)):
                    continue

                mod_str = cls.format_modifications_string(combo)

                # Simulate ledger under this spending adjustment
                ledger = DailyLedger(
                    user=user,
                    request_date=request.request_date,
                    days=90,
                    recurring_streams=recurring_streams,
                    future_events=future_events,
                    spending_modifications=mod_str,
                )

                # 1. Check if savings from this modification combo directly cover shortfall for full payment
                combo_savings = 0.0
                for action, ev_id, min_amt, _ in combo:
                    matching = [s for s in recurring_streams if s.latest_event_id == ev_id]
                    if matching:
                        st = matching[0]
                        if action == "stop":
                            combo_savings += st.baseline_amount
                        elif action == "reduce_to" and min_amt is not None:
                            combo_savings += max(0.0, st.baseline_amount - min_amt)

                shortfall = float(request.requested_amount) - safe_amt_baseline
                is_full_viable = False
                if user.will_consider("full_payment") and shortfall > 0:
                    if combo_savings >= (shortfall * 0.95):
                        is_full_viable = True
                    elif combo_savings > 0 and (safe_amt_baseline + combo_savings >= float(request.requested_amount) * 0.85):
                        is_full_viable = True

                if is_full_viable:
                    plan_str = f"{request.request_date}:{format_plan_amount(request.requested_amount)}"
                    earliest = earliest_full_date if earliest_full_date else request.request_date
                    full_cand = CandidatePlan(
                        payment_method=PaymentMethod.FULL_PAYMENT,
                        payment_plan=plan_str,
                        first_payment_date=request.request_date,
                        total_payable_amount=float(request.requested_amount),
                        number_of_payments=1,
                        spending_changes_needed=mod_str,
                        payment_option_id="none",
                        completes_by_deadline=(request.request_date <= request.desired_completion_date),
                        requires_spending_changes=True,
                        affordability_status=AffordabilityStatus.AFFORDABLE_WITH_PLAN,
                        earliest_date_for_full_payment=earliest,
                        amount_safe_to_pay=safe_amt_baseline,
                    )
                    if full_cand.completes_by_deadline:
                        k_level_plans.append(full_cand)
                else:
                    # 1b. Test simulated full payment candidate
                    full_cand = CandidateGenerator.generate_full_payment_candidate(
                        request=request,
                        user=user,
                        ledger=ledger,
                        spending_changes=mod_str,
                        earliest_full_date=earliest_full_date,
                        safe_amt_baseline=safe_amt_baseline,
                    )
                    if full_cand and full_cand.completes_by_deadline:
                        k_level_plans.append(full_cand)

                # 2. Installment options
                inst_cands = CandidateGenerator.generate_installment_candidates(
                    request=request,
                    user=user,
                    options=options,
                    ledger=ledger,
                    spending_changes=mod_str,
                    earliest_full_date=earliest_full_date,
                    safe_amt_baseline=safe_amt_baseline,
                )
                for c in inst_cands:
                    if c.completes_by_deadline:
                        k_level_plans.append(c)

            if k_level_plans:
                # We found successful plans at this level of modifications!
                # Prioritize minimal disruption: return the best plans from the smallest k
                successful_plans.extend(k_level_plans)
                break

        return successful_plans
