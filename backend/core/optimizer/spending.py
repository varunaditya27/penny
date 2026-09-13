import itertools
import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.core.models.domain import PaymentOption, PurchaseRequest, UserProfile
from backend.core.models.results import AffordabilityStatus, CandidatePlan, PaymentMethod
from backend.core.optimizer.candidates import CandidateGenerator, format_plan_amount
from backend.core.optimizer.ranker import PlanRanker
from backend.core.simulation.ledger import DailyLedger
from backend.core.simulation.recurrence import RecurringStream

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


            # Rule 2: Check reducible (preferred over complete stoppage when minimum allowed amount exists)
            if (
                user.can_reduce_category(cat)
                and stream.flexibility in ["reducible", "reducible_or_stoppable"]
                and stream.minimum_allowed_amount is not None
            ):
                key = ("reduce_to", ev_id, stream.minimum_allowed_amount)
                if key not in seen_keys:
                    seen_keys.add(key)
                    mods_with_date.append(("reduce_to", ev_id, stream.minimum_allowed_amount, cat, stream.latest_date))

            # Rule 3: Check stoppable (for purely stoppable streams, or if user volunteered to stop and no reduction available)
            if user.can_stop_category(cat) and stream.flexibility in ["stoppable", "reducible_or_stoppable"]:
                # If stream is already reducible and has a minimum allowed amount, prefer reduction; otherwise allow stop
                if stream.flexibility == "stoppable" or stream.minimum_allowed_amount is None:
                    key = ("stop", ev_id)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        mods_with_date.append(("stop", ev_id, None, cat, stream.latest_date))

        def sort_key(m):
            action, ev_id, min_amt, cat, dt = m
            # Priority 1: Categories user is willing to stop (subscriptions) first
            stop_volunteered = 0 if user.can_stop_category(cat) else 1
            # Priority 2: Action 'stop' before 'reduce_to'
            act_order = 0 if action == "stop" else 1
            # Priority 3: Newer records first
            date_int = -int(dt.replace("-", "")) if dt else 0
            return (stop_volunteered, act_order, date_int)

        mods_with_date.sort(key=sort_key)
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
        events_map: Optional[Dict[str, Any]] = None,
    ) -> List[CandidatePlan]:
        """
        Combinatorially searches subsets of size 1, 2, ..., max_modifications.
        For each valid subset, evaluates candidate payment plans under the modified budget.
        Returns all plans that successfully complete by desired_completion_date.
        """
        eligible_mods = cls.get_eligible_modifications(user, recurring_streams)
        if not eligible_mods:
            return []

        def _evaluate_pool(
            mods_pool: List[Tuple[str, str, Optional[float], str]], is_tier1: bool = False
        ) -> List[CandidatePlan]:
            pool_plans: List[CandidatePlan] = []
            for k in range(1, min(max_modifications, len(mods_pool)) + 1):
                k_level_plans: List[CandidatePlan] = []

                for combo in itertools.combinations(mods_pool, k):
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

                    # Every recommendation must be backed by its full 90-day ledger.
                    # Savings estimates are useful for search ordering, never as proof
                    # that a payment is financially safe.
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
                    pool_plans.extend(k_level_plans)
                    break

            return pool_plans

        # Two-stage search:
        # Tier 1: Search categories user explicitly volunteered to stop first (e.g. streaming, cloud_storage)
        willing_stop_mods = [m for m in eligible_mods if user.can_stop_category(m[3])]
        if willing_stop_mods:
            tier1_plans = _evaluate_pool(willing_stop_mods, is_tier1=True)
            if tier1_plans:
                return tier1_plans

        # Tier 2: Fallback to all eligible modifications
        return _evaluate_pool(eligible_mods, is_tier1=False)
