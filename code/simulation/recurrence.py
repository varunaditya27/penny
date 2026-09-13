import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple, Set

from code.models.domain import FinancialEvent

logger = logging.getLogger("buy_or_wait.simulation.recurrence")


@dataclass
class RecurringStream:
    """
    Represents a detected recurring cash flow stream for a user.
    Can be a calendar day-of-month fixed expense/income or an integer day-step cadence.
    """
    description: str
    category: str
    cadence_type: str  # 'dom' or 'step'
    step_days: Optional[int]
    day_of_month: Optional[int]
    baseline_amount: float
    latest_date: str
    latest_event_id: str
    flexibility: str = "fixed"
    minimum_allowed_amount: Optional[float] = None
    direction: str = "debit"  # 'debit' or 'credit'
    effective_date: Optional[str] = None
    post_effective_amount: Optional[float] = None

    @property
    def is_credit(self) -> bool:
        return self.direction == "credit" or self.category == "salary"

    @property
    def is_debit(self) -> bool:
        return not self.is_credit


class RecurrenceDetector:
    """
    Analyzes historical settled financial events for a user.
    Detects fixed calendar day-of-month (DOM) recurrence and integer day-step cadences.
    """
    STEP_CANDIDATES: Set[int] = {5, 7, 10, 14, 21}

    @classmethod
    def _is_step_cadence(cls, events: List[FinancialEvent]) -> Tuple[bool, Optional[int]]:
        """
        Determines whether events occur at a fixed integer day-step in {5, 7, 10, 14, 21}.
        Allows minor single-event date jitter (e.g. bank holidays) if >= 75% match.
        """
        if len(events) < 2:
            return False, None
        
        # Extract unique sorted event dates
        dates = sorted(set(datetime.strptime(e.event_date, "%Y-%m-%d") for e in events))
        if len(dates) < 2:
            return False, None

        deltas = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        counts = Counter(deltas)
        mode_delta, count = counts.most_common(1)[0]

        if mode_delta in cls.STEP_CANDIDATES:
            # Either 100% agreement or at least 75% dominant cadence for long series (>= 3 transitions)
            if count == len(deltas) or (len(deltas) >= 3 and (count / len(deltas)) >= 0.75):
                return True, mode_delta

        return False, None

    @classmethod
    def _is_dom_cadence(cls, events: List[FinancialEvent]) -> Tuple[bool, Optional[int]]:
        """
        Determines whether events occur on a fixed calendar day of the month.
        Requires >= 2 occurrences.
        """
        if len(events) < 2:
            return False, None

        dom_counts = Counter(datetime.strptime(e.event_date, "%Y-%m-%d").day for e in events)
        mode_dom, count = dom_counts.most_common(1)[0]

        # Exact match or at most 1 anomaly in >= 4 events
        if count == len(events) or (len(events) >= 4 and count >= len(events) - 1):
            return True, mode_dom

        return False, None

    @classmethod
    def detect_streams(cls, events: List[FinancialEvent]) -> List[RecurringStream]:
        """
        Analyzes settled FinancialEvent records, clustering by description and category.
        Detects fixed day-of-month and integer day-step cadences.
        """
        # Filter strictly settled, positive-cash events, excluding non-cash / unrealized
        settled = [
            e for e in events
            if e.status == "settled" and e.amount is not None and e.amount > 0 and not e.is_non_cash
        ]

        # Cluster by category first
        by_cat = defaultdict(list)
        for e in settled:
            by_cat[e.category].append(e)

        streams: List[RecurringStream] = []

        for cat, c_evs in by_cat.items():
            c_evs.sort(key=lambda x: x.event_date)

            # 1. Check if category as a whole forms an integer day-step cadence (e.g. groceries, transport, dining)
            ok_step, step = cls._is_step_cadence(c_evs)
            if ok_step:
                latest = c_evs[-1]
                amounts = [e.amount for e in c_evs if e.amount is not None]
                import statistics
                if len(amounts) >= 3:
                    med = statistics.median(amounts)
                    # Use median if latest event is an extreme outlier (e.g. bulk pantry purchase > 2x median)
                    base_amt = med if (latest.amount > 2.0 * med) else latest.amount
                else:
                    base_amt = latest.amount
                streams.append(RecurringStream(
                    description=latest.description,
                    category=cat,
                    cadence_type="step",
                    step_days=step,
                    day_of_month=None,
                    baseline_amount=base_amt,
                    latest_date=latest.event_date,
                    latest_event_id=latest.event_id,
                    flexibility=latest.flexibility,
                    minimum_allowed_amount=latest.minimum_allowed_amount,
                    direction=latest.direction
                ))
                continue

            # 2. Check if category as a whole forms a day-of-month cadence (e.g. rent, utilities, subscriptions)
            ok_dom, dom = cls._is_dom_cadence(c_evs)
            if ok_dom:
                matching = [e for e in c_evs if datetime.strptime(e.event_date, "%Y-%m-%d").day == dom]
                latest = matching[-1] if matching else c_evs[-1]
                streams.append(RecurringStream(
                    description=latest.description,
                    category=cat,
                    cadence_type="dom",
                    step_days=None,
                    day_of_month=dom,
                    baseline_amount=latest.amount,
                    latest_date=latest.event_date,
                    latest_event_id=latest.event_id,
                    flexibility=latest.flexibility,
                    minimum_allowed_amount=latest.minimum_allowed_amount,
                    direction=latest.direction
                ))
                continue

            # 3. If category is not pure as a whole, cluster by description within category
            by_desc = defaultdict(list)
            for e in c_evs:
                by_desc[e.description].append(e)

            for desc, d_evs in by_desc.items():
                if len(d_evs) < 2:
                    continue
                d_evs.sort(key=lambda x: x.event_date)

                ok_step, step = cls._is_step_cadence(d_evs)
                if ok_step:
                    latest = d_evs[-1]
                    streams.append(RecurringStream(
                        description=desc,
                        category=cat,
                        cadence_type="step",
                        step_days=step,
                        day_of_month=None,
                        baseline_amount=latest.amount,
                        latest_date=latest.event_date,
                        latest_event_id=latest.event_id,
                        flexibility=latest.flexibility,
                        minimum_allowed_amount=latest.minimum_allowed_amount,
                        direction=latest.direction
                    ))
                    continue

                ok_dom, dom = cls._is_dom_cadence(d_evs)
                if ok_dom:
                    matching = [e for e in d_evs if datetime.strptime(e.event_date, "%Y-%m-%d").day == dom]
                    latest = matching[-1] if matching else d_evs[-1]
                    streams.append(RecurringStream(
                        description=desc,
                        category=cat,
                        cadence_type="dom",
                        step_days=None,
                        day_of_month=dom,
                        baseline_amount=latest.amount,
                        latest_date=latest.event_date,
                        latest_event_id=latest.event_id,
                        flexibility=latest.flexibility,
                        minimum_allowed_amount=latest.minimum_allowed_amount,
                        direction=latest.direction
                    ))

        logger.debug(f"RecurrenceDetector found {len(streams)} recurring streams from {len(settled)} settled events.")
        return streams
