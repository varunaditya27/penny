import itertools
import logging
from typing import List, Optional, Tuple

from code.models.domain import PaymentOption, PurchaseRequest, UserProfile
from code.models.results import CandidatePlan
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
        mods: List[Tuple[str, str, Optional[float], str]] = []
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
                    mods.append(("stop", ev_id, None, cat))

            # Rule 3: Check reducible
            if (
                user.can_reduce_category(cat)
                and stream.flexibility in ["reducible", "reducible_or_stoppable"]
                and stream.minimum_allowed_amount is not None
            ):
                key = ("reduce_to", ev_id, stream.minimum_allowed_amount)
                if key not in seen_keys:
                    seen_keys.add(key)
                    mods.append(("reduce_to", ev_id, stream.minimum_allowed_amount, cat))

        return mods

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

                # 1. Full payment option
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
