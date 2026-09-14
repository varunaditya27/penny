import calendar
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Union

from backend.core.models.domain import FinancialEvent, UserProfile
from backend.core.simulation.recurrence import RecurringStream

logger = logging.getLogger("buy_or_wait.simulation.ledger")


class DailyLedger:
    """
    Simulates a user's daily available cash balance over a forecast horizon (default 90 days).
    Incorporates:
    - Initial available balance on request_date
    - Forward-projected recurring streams (DOM and integer day-step)
    - Confirmed scheduled future credits on settlement dates
    - Pending and scheduled debits on settlement dates
    - Candidate plan payments on specified dates
    - Permitted spending modifications (stop:<event_id> and reduce_to:<event_id>:<amount>)
    """

    def __init__(
        self,
        user: UserProfile,
        request_date: str,
        days: int = 90,
        recurring_streams: Optional[List[RecurringStream]] = None,
        future_events: Optional[List[FinancialEvent]] = None,
        spending_modifications: Optional[Union[str, List[str]]] = None,
        candidate_payments: Optional[Union[Dict[str, float], List[Tuple[str, float]], str]] = None,
    ):
        self.user = user
        self.request_date = request_date
        self.days = days
        self.recurring_streams: List[RecurringStream] = recurring_streams or []
        self.future_events: List[FinancialEvent] = future_events or []
        self.spending_modifications: Optional[Union[str, List[str]]] = spending_modifications
        self.candidate_payments = candidate_payments

        self.dates: List[str] = []
        self.balances: List[float] = []

        self._simulate()

    def _parse_spending_modifications(self) -> Tuple[Set[str], Dict[str, float]]:
        stopped_event_ids: Set[str] = set()
        reduced_amounts: Dict[str, float] = {}

        if not self.spending_modifications or self.spending_modifications == "none":
            return stopped_event_ids, reduced_amounts

        mods_list: List[str] = []
        if isinstance(self.spending_modifications, str):
            mods_list = [m.strip() for m in self.spending_modifications.split("|") if m.strip()]
        elif isinstance(self.spending_modifications, list):
            for m in self.spending_modifications:
                if isinstance(m, str):
                    for sub in m.split("|"):
                        if sub.strip():
                            mods_list.append(sub.strip())

        for mod in mods_list:
            if mod == "none":
                continue
            parts = mod.split(":")
            action = parts[0]
            if action == "stop" and len(parts) >= 2:
                stopped_event_ids.add(parts[1])
            elif action == "reduce_to" and len(parts) >= 3:
                try:
                    event_id = parts[1]
                    target_amt = float(parts[2])
                    reduced_amounts[event_id] = target_amt
                except ValueError:
                    logger.warning(f"Could not parse reduce_to target amount in modification: {mod}")

        return stopped_event_ids, reduced_amounts

    def _parse_candidate_payments(self) -> Dict[str, float]:
        payments_by_date: Dict[str, float] = defaultdict(float)
        if not self.candidate_payments:
            return payments_by_date

        if isinstance(self.candidate_payments, str):
            if self.candidate_payments == "none":
                return payments_by_date
            for entry in self.candidate_payments.split("|"):
                entry = entry.strip()
                if not entry:
                    continue
                parts = entry.split(":")
                if len(parts) == 2:
                    try:
                        payments_by_date[parts[0]] += float(parts[1])
                    except ValueError:
                        pass
        elif isinstance(self.candidate_payments, dict):
            for dt, amt in self.candidate_payments.items():
                payments_by_date[dt] += float(amt)
        elif isinstance(self.candidate_payments, list):
            for item in self.candidate_payments:
                if isinstance(item, (tuple, list)) and len(item) == 2:
                    payments_by_date[str(item[0])] += float(item[1])

        return payments_by_date

    def _simulate(self) -> None:
        start_dt = datetime.strptime(self.request_date, "%Y-%m-%d")
        stopped_ids, reduced_amts = self._parse_spending_modifications()
        payments_by_date = self._parse_candidate_payments()

        # Pre-filter and group future events by settlement date
        events_by_date: Dict[str, List[FinancialEvent]] = defaultdict(list)
        for ev in self.future_events:
            # Ignore non-cash, unrealized, failed, or cancelled
            if ev.is_non_cash or ev.status in ["failed", "cancelled", "unrealized"]:
                continue
            if ev.amount is None:
                logger.error(f"Event {ev.event_id} has None amount; excluding from cash flow to avoid treating blank as zero.")
                continue
            s_date = ev.settlement_date or ev.event_date
            events_by_date[s_date].append(ev)

        # Precompute parsed datetime objects for recurring stream latest_date
        stream_starts = {
            s.latest_event_id: datetime.strptime(s.latest_date, "%Y-%m-%d")
            for s in self.recurring_streams
            if s.latest_date
        }

        # When a confirmed salary arrives well after the request date, budget one
        # observed step-cadence expense in the pre-salary window if its established
        # cadence has no natural occurrence there. This protects essential variable
        # spending before the next cash inflow without altering the recurring cadence.
        first_sal_dt = None
        for stream in self.recurring_streams:
            if stream.is_credit and stream.category == "salary" and stream.day_of_month:
                for d in range(1, 35):
                    cand = start_dt + timedelta(days=d)
                    max_d = calendar.monthrange(cand.year, cand.month)[1]
                    if cand.day == min(stream.day_of_month, max_d):
                        first_sal_dt = cand
                        break
                if first_sal_dt:
                    break

        extra_step_fires: Dict[str, Set[str]] = defaultdict(set)
        if first_sal_dt and (first_sal_dt - start_dt).days >= 7:
            trough_date_str = (first_sal_dt - timedelta(days=2)).strftime("%Y-%m-%d")
            for stream in self.recurring_streams:
                if stream.cadence_type == "step" and stream.step_days and not stream.is_credit:
                    stream_start = stream_starts[stream.latest_event_id]
                    natural_fire = False
                    cur = start_dt
                    while cur < first_sal_dt:
                        d_days = (cur - stream_start).days
                        if d_days > 0 and d_days % stream.step_days == 0:
                            natural_fire = True
                            break
                        cur += timedelta(days=1)
                    if not natural_fire:
                        extra_step_fires[trough_date_str].add(stream.latest_event_id)

        self.dates = []
        self.balances = []
        current_balance = float(self.user.current_available_balance)

        for t in range(self.days + 1):
            curr_dt = start_dt + timedelta(days=t)
            curr_str = curr_dt.strftime("%Y-%m-%d")
            self.dates.append(curr_str)

            day_credits = 0.0
            day_debits = 0.0

            # 1. Process future one-off / pending events on this settlement date
            if curr_str in events_by_date:
                for ev in events_by_date[curr_str]:
                    if ev.amount is None:
                        logger.error(f"Event {ev.event_id} has None amount; skipping to prevent treating blank as zero.")
                        continue
                    amt = float(ev.amount)
                    if ev.is_debit:
                        # Subtract pending or scheduled debits
                        if ev.status in ["pending", "scheduled", "settled"]:
                            day_debits += amt
                    elif ev.is_credit:
                        # Add confirmed future scheduled credits per §6.3:
                        # "Do not count pending credits, bonuses, commissions, refunds, lottery proceeds, or investment gains until they settle."
                        if ev.status == "scheduled":
                            day_credits += amt

            # 2. Process recurring streams
            for stream in self.recurring_streams:
                if stream.latest_event_id in stopped_ids:
                    continue

                base_amt = reduced_amts.get(stream.latest_event_id, stream.baseline_amount)
                effective_amt = base_amt
                if stream.effective_date and stream.post_effective_amount is not None:
                    if curr_str >= stream.effective_date:
                        effective_amt = stream.post_effective_amount
                fires = False

                if stream.cadence_type == "step":
                    if stream.step_days and stream.step_days > 0:
                        stream_start = stream_starts[stream.latest_event_id]
                        delta_days = (curr_dt - stream_start).days
                        if delta_days > 0 and delta_days % stream.step_days == 0:
                            fires = True
                        elif curr_str in extra_step_fires and stream.latest_event_id in extra_step_fires[curr_str]:
                            fires = True
                elif stream.cadence_type == "dom":
                    if stream.day_of_month:
                        max_day = calendar.monthrange(curr_dt.year, curr_dt.month)[1]
                        effective_dom = min(stream.day_of_month, max_day)
                        if curr_str > stream.latest_date and curr_dt.day == effective_dom:
                            fires = True

                if fires:
                    if stream.is_credit:
                        day_credits += effective_amt
                    else:
                        day_debits += effective_amt

            # 3. Process candidate payments scheduled for this date
            if curr_str in payments_by_date:
                day_debits += payments_by_date[curr_str]

            current_balance += day_credits - day_debits
            self.balances.append(round(current_balance, 2))

    def is_safe(self) -> bool:
        """True if min(balance[t]) >= user.minimum_balance_to_keep for all t in [0, days]."""
        return min(self.balances) >= self.user.minimum_balance_to_keep

    def min_headroom(self) -> float:
        """Returns the minimum cushion above minimum_balance_to_keep across all days."""
        return round(min(b - self.user.minimum_balance_to_keep for b in self.balances), 2)

    def balance_at(self, day_idx: int) -> float:
        """Returns the projected balance on day t."""
        if 0 <= day_idx < len(self.balances):
            return self.balances[day_idx]
        raise IndexError(f"Day index {day_idx} out of range [0, {len(self.balances) - 1}]")

    def balance_on(self, date_str: str) -> Optional[float]:
        """Returns projected balance on the given YYYY-MM-DD date."""
        try:
            idx = self.dates.index(date_str)
            return self.balances[idx]
        except ValueError:
            return None

    def headroom_at(self, day_idx: int) -> float:
        """Returns cushion above minimum balance on day t."""
        return round(self.balance_at(day_idx) - self.user.minimum_balance_to_keep, 2)

    def headroom_on(self, date_str: str) -> Optional[float]:
        """Returns cushion above minimum balance on the given YYYY-MM-DD date."""
        bal = self.balance_on(date_str)
        if bal is not None:
            return round(bal - self.user.minimum_balance_to_keep, 2)
        return None

    def get_daily_balances(self) -> List[float]:
        return list(self.balances)

    def get_dates(self) -> List[str]:
        return list(self.dates)
