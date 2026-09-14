import logging
from collections import Counter
from typing import Any, Dict, List, Optional, Union

from backend.core.data.classifier import IncomeStreamClassifier
from backend.core.data.currency import ExchangeRateConverter
from backend.core.data.evidence import EvidenceManager
from backend.core.data.linker import EventLinker
from backend.core.models.domain import FinancialEvent, UserProfile
from backend.core.simulation.ledger import DailyLedger
from backend.core.simulation.recurrence import RecurrenceDetector, RecurringStream

logger = logging.getLogger("buy_or_wait.simulation.builder")


class _BuildLedgerDescriptor:
    def __get__(self, instance, owner):
        def _wrapper(
            user: UserProfile,
            events: List[FinancialEvent],
            request_date: str,
            days: int = 90,
            candidate_payments: Optional[Any] = None,
            converter: Optional[ExchangeRateConverter] = None,
            evidence_mgr: Optional[EvidenceManager] = None,
            income_classifier: Optional[IncomeStreamClassifier] = None,
        ) -> DailyLedger:
            conv = (
                converter
                or (getattr(instance, "converter", None) if instance else None)
                or ExchangeRateConverter()
            )
            ev_mgr = (
                evidence_mgr
                or (getattr(instance, "evidence_mgr", None) if instance else None)
                or EvidenceManager()
            )
            classifier = (
                income_classifier
                or (getattr(instance, "income_classifier", None) if instance else None)
                or IncomeStreamClassifier()
            )
            return SimulationLedgerBuilder._build_ledger_impl(
                user=user,
                events=events,
                request_date=request_date,
                days=days,
                candidate_payments=candidate_payments,
                converter=conv,
                evidence_mgr=ev_mgr,
                income_classifier=classifier,
            )

        return _wrapper


class SimulationLedgerBuilder:
    """
    Coordinates building a DailyLedger for simulation:
    - Non-cash filtering
    - Event linking (via EventLinker)
    - Currency normalization (via ExchangeRateConverter)
    - Partitioning into historical settled vs pending/scheduled future events
    - Recurring debit stream detection (via RecurrenceDetector)
    - Confirmed ongoing salary stream extraction
    """

    build_ledger = _BuildLedgerDescriptor()

    def __init__(
        self,
        converter: Optional[ExchangeRateConverter] = None,
        evidence_mgr: Optional[EvidenceManager] = None,
        income_classifier: Optional[IncomeStreamClassifier] = None,
    ):
        self.converter = converter or ExchangeRateConverter()
        self.evidence_mgr = evidence_mgr or EvidenceManager()
        self.income_classifier = income_classifier or IncomeStreamClassifier()

    @classmethod
    def extract_recurring_salary_stream(
        cls,
        user: UserProfile,
        request_date: str,
        hist_events: List[FinancialEvent],
        future_events: List[FinancialEvent],
        user_mutations: Optional[List[Dict[str, Any]]] = None,
        converter: Optional[ExchangeRateConverter] = None,
        income_classifier: Optional[IncomeStreamClassifier] = None,
    ) -> Optional[RecurringStream]:
        """
        Determines the confirmed ongoing recurring salary stream, if any.
        Obeys problem statement rules:
        - Exclude commissions, bonuses, lottery, refunds, portfolio gains.
        - Stop salary if message says STOP_INCOME or description says 'final' / 'seasonal' / 'temporary'.
        - Use mode of day-of-month across historical payroll events.
        """
        mutations = user_mutations or []
        conv = converter or ExchangeRateConverter()
        classifier = income_classifier or IncomeStreamClassifier()

        stop_income = any(m.get("action") == "STOP_INCOME" for m in mutations)
        if stop_income:
            return None

        # Check for future scheduled salary
        sched_salaries = [
            e
            for e in future_events
            if e.category == "salary" or "salary" in e.description.lower() or "payroll" in e.description.lower()
        ]

        # Check all historical salaries to verify if employment is still active
        all_hist_salaries = [
            e
            for e in hist_events
            if (e.category == "salary" or "salary" in e.description.lower() or "payroll" in e.description.lower())
        ]
        if all_hist_salaries:
            latest_hist = sorted(all_hist_salaries, key=lambda x: x.event_date)[-1]
            desc = latest_hist.description.lower()
            if "final" in desc or "seasonal" in desc or "temporary" in desc:
                # Terminated contract, seasonal work, or final payroll
                return None

        settled_salaries = [
            e
            for e in all_hist_salaries
            if classifier.is_recurring_income(e.description)
        ]

        if sched_salaries:
            sched = sorted(sched_salaries, key=lambda x: x.event_date)[-1]
            dom = int(sched.event_date.split("-")[2])
            sched_amt = float(sched.amount) if sched.amount is not None else 0.0
            if sched.currency and sched.currency != user.home_currency:
                sched_amt = round(conv.convert(sched_amt, sched.currency, user.home_currency, sched.event_date), 2)
            return RecurringStream(
                description=sched.description,
                category="salary",
                cadence_type="dom",
                step_days=None,
                day_of_month=dom,
                baseline_amount=sched_amt,
                latest_date=sched.event_date,
                latest_event_id=sched.event_id,
                direction="credit",
            )

        if settled_salaries:
            latest_settled = sorted(settled_salaries, key=lambda x: x.event_date)[-1]

            # Calculate statistical mode of day of month across salary history
            doms = [int(e.event_date.split("-")[2]) for e in settled_salaries]
            mode_dom = Counter(doms).most_common(1)[0][0]

            # Check if payroll date was amended in messages
            for m in mutations:
                if m.get("action") == "AMEND_PAYROLL_DATE" and m.get("effective_date"):
                    eff = m["effective_date"]
                    mode_dom = int(eff.split("-")[2])
                    logger.info(f"Overrode salary DOM to {mode_dom} from payroll amendment message")

            amt = latest_settled.amount
            if latest_settled.currency and latest_settled.currency != user.home_currency and amt is not None:
                amt = round(conv.convert(amt, latest_settled.currency, user.home_currency, latest_settled.event_date), 2)

            eff_date = None
            post_eff_amt = None
            for m in mutations:
                if m.get("action") == "AMEND_SALARY" and m.get("amount"):
                    m_eff = m.get("effective_date")
                    if m_eff and m_eff > request_date:
                        eff_date = m_eff
                        post_eff_amt = float(m["amount"])
                    else:
                        amt = float(m["amount"])

            return RecurringStream(
                description=latest_settled.description,
                category="salary",
                cadence_type="dom",
                step_days=None,
                day_of_month=mode_dom,
                baseline_amount=amt,
                latest_date=latest_settled.event_date,
                latest_event_id=latest_settled.event_id,
                direction="credit",
                effective_date=eff_date,
                post_effective_amount=post_eff_amt,
            )

        # Check for new job announced in messages
        for m in mutations:
            if m.get("action") in ["NEW_JOB", "NEW_JOB_SALARY"] and m.get("amount"):
                eff = m.get("effective_date", request_date)
                dom = int(eff.split("-")[2]) if "-" in eff else 15
                return RecurringStream(
                    description="Confirmed new employment salary",
                    category="salary",
                    cadence_type="dom",
                    step_days=None,
                    day_of_month=dom,
                    baseline_amount=float(m["amount"]),
                    latest_date=eff,
                    latest_event_id="msg_salary",
                    direction="credit",
                )

        return None

    @classmethod
    def _build_ledger_impl(
        cls,
        user: UserProfile,
        events: List[FinancialEvent],
        request_date: str,
        days: int = 90,
        candidate_payments: Optional[Any] = None,
        converter: Optional[ExchangeRateConverter] = None,
        evidence_mgr: Optional[EvidenceManager] = None,
        income_classifier: Optional[IncomeStreamClassifier] = None,
    ) -> DailyLedger:
        conv = converter or ExchangeRateConverter()
        ev_mgr = evidence_mgr or EvidenceManager()
        classifier = income_classifier or IncomeStreamClassifier()

        # 1. Evidence reconciliation: apply image extractions and message mutations
        augmented_events = ev_mgr.apply_evidence_to_events(
            events=events,
            user_id=user.user_id,
            request_date=request_date,
            home_currency=user.home_currency,
        )

        # 1a. Event linking and non-cash reconciliation
        augmented_events = EventLinker.resolve_linked_events(augmented_events)

        # 1b. Foreign currency conversion to user home currency
        for ev in augmented_events:
            if ev.amount is not None and ev.currency and ev.currency != user.home_currency:
                ev_date = ev.settlement_date or ev.event_date
                ev.amount = round(conv.convert(ev.amount, ev.currency, user.home_currency, ev_date), 2)
                ev.currency = user.home_currency

        # 2. Partition events into historical settled and future/pending
        hist_events: List[FinancialEvent] = []
        future_events: List[FinancialEvent] = []

        for ev in augmented_events:
            # Skip non-cash, failed, cancelled, or unrealized investments
            if ev.is_non_cash or ev.status in ["failed", "cancelled", "unrealized"]:
                continue
            if ev.amount is None:
                logger.error(
                    f"Event {ev.event_id} has None amount after evidence processing; excluding from cash flow to avoid treating blank as zero."
                )
                continue

            if ev.event_date <= request_date and ev.status == "settled":
                hist_events.append(ev)
            elif ev.status in ["pending", "scheduled"] or ev.event_date > request_date:
                future_events.append(ev)

        # 3. Detect recurring streams from historical settled events
        streams = RecurrenceDetector.detect_streams(hist_events)

        # Discard any credit streams detected automatically; auto-detection only keeps expense/debit streams
        streams = [s for s in streams if not s.is_credit]

        # 4. Integrate robust confirmed ongoing salary stream
        user_mutations = ev_mgr.get_user_mutations(user.user_id, request_date)
        salary_stream = cls.extract_recurring_salary_stream(
            user=user,
            request_date=request_date,
            hist_events=hist_events,
            future_events=future_events,
            user_mutations=user_mutations,
            converter=conv,
            income_classifier=classifier,
        )
        if salary_stream is not None:
            streams.append(salary_stream)

        # 5. Baseline Simulation Ledger
        return DailyLedger(
            user=user,
            request_date=request_date,
            days=days,
            recurring_streams=streams,
            future_events=future_events,
            candidate_payments=candidate_payments,
        )
